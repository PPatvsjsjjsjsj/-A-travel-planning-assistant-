import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from config.settings import SKILLS_DIR
from agents.travel_agent import TravelAgent
from messaging.session_store import SessionStore
from services.map_routes import build_map_route
from services.request_parser import parse_natural_request
from services.travel_planner import create_trip_plan
from skills.loader import SkillLoader


class TravelPlannerTests(unittest.TestCase):
    def test_parse_natural_request(self):
        request = parse_natural_request("我想从杭州去西安，玩4天，2个人，经济预算，喜欢历史和美食")
        self.assertEqual(request.origin, "杭州")
        self.assertEqual(request.destination, "西安")
        self.assertEqual(request.days, 4)
        self.assertEqual(request.travelers, 2)
        self.assertEqual(request.budget_level, "经济")
        self.assertEqual(request.interests, ["历史", "美食"])

    def test_local_plan_without_api_key(self):
        request = parse_natural_request("从北京去成都，玩3天")
        plan = asyncio.run(create_trip_plan(request))
        self.assertEqual(plan.destination, "成都")
        self.assertEqual(len(plan.itinerary), 3)
        self.assertEqual(plan.source, "local_demo")

    def test_skill_catalog_and_selection(self):
        loader = SkillLoader(SKILLS_DIR)
        self.assertEqual(len(loader.list_skills()), 11)
        request = parse_natural_request("从上海去云南自驾5天，有花生过敏，想参加节庆活动")
        selected, context = loader.build_context(request)
        self.assertIn("route-planning", selected)
        self.assertIn("enroute-attractions", selected)
        self.assertIn("dietary-taboos", selected)
        self.assertIn("festival-etiquette", selected)
        self.assertIn("travel-preparation", selected)
        self.assertIn("<skill", context)

    def test_transport_phrase_parsing(self):
        request = parse_natural_request("从北京坐高铁去杭州，玩3天，喜欢摄影")
        self.assertEqual(request.origin, "北京")
        self.assertEqual(request.destination, "杭州")
        self.assertEqual(request.transport_preference, "高铁")

    def test_agent_can_update_existing_plan(self):
        agent = TravelAgent(SessionStore(), SkillLoader(SKILLS_DIR))
        first = asyncio.run(agent.chat("从上海去成都，玩3天，2个人"))
        updated = asyncio.run(agent.chat("改成5天，预算改成经济", first.session_id))
        self.assertEqual(first.stage, "planned")
        self.assertEqual(updated.stage, "updated")
        self.assertEqual(updated.request.days, 5)
        self.assertEqual(updated.request.budget_level, "经济")
        self.assertEqual(len(updated.plan.itinerary), 5)

    def test_agent_voice_is_wangge(self):
        agent = TravelAgent(SessionStore(), SkillLoader(SKILLS_DIR))
        response = asyncio.run(agent.chat("你好"))
        self.assertIn("王哥", response.reply)

    def test_vague_route_collects_details_before_planning(self):
        agent = TravelAgent(SessionStore(), SkillLoader(SKILLS_DIR))
        response = asyncio.run(agent.chat("西安去北京"))
        self.assertEqual(response.stage, "collecting")
        self.assertIsNone(response.plan)
        self.assertIn("高铁", response.reply)
        self.assertIn("玩几天", response.reply)

        planned = asyncio.run(agent.chat("坐高铁，玩5天，2个人", response.session_id))
        self.assertEqual(planned.stage, "updated")
        self.assertEqual(planned.request.travelers, 2)
        self.assertEqual(planned.plan.days, 5)
        self.assertIn("怎么去", planned.reply)
        self.assertIn("出发前准备", planned.reply)
        self.assertIn("当地风土人情", planned.reply)

    def test_plan_has_concrete_transport_and_preparation(self):
        request = parse_natural_request("从北京坐高铁去杭州，玩3天，2个人")
        plan = asyncio.run(create_trip_plan(request))
        transport = plan.transport_options[0]
        self.assertEqual(transport.departure, "北京南站")
        self.assertEqual(transport.arrival, "杭州东站")
        self.assertGreaterEqual(len(transport.steps), 3)
        self.assertNotIn("12306", transport.route + transport.advice)
        self.assertGreaterEqual(len(plan.preparation.destination_specific), 1)
        self.assertIn("不含往返大交通", plan.budget.note)

    def test_map_route_uses_real_city_coordinates(self):
        route = build_map_route("上海市", "成都市", "高铁")
        self.assertEqual(route.origin, "上海")
        self.assertEqual(route.destination, "成都")
        self.assertEqual(route.transport, "高铁")
        self.assertGreater(route.distance_km, 1500)
        self.assertEqual(route.points[0].kind, "origin")
        self.assertEqual(route.points[-1].kind, "destination")

    def test_map_route_uses_real_transport_hubs(self):
        rail = build_map_route("西安", "北京", "高铁")
        self.assertEqual([point.name for point in rail.points], ["西安北站", "北京南站"])
        flight = build_map_route("西安", "北京", "飞机")
        self.assertEqual([point.name for point in flight.points], ["西安咸阳国际机场", "北京首都国际机场"])

    def test_driving_route_contains_realistic_corridor(self):
        route = build_map_route("广州", "桂林", "自驾")
        self.assertEqual([point.name for point in route.points], ["广州", "肇庆", "贺州", "阳朔", "桂林"])

    def test_agent_answers_travel_follow_up(self):
        agent = TravelAgent(SessionStore(), SkillLoader(SKILLS_DIR))
        planned = asyncio.run(agent.chat("从广州自驾去桂林，玩4天"))
        answer = asyncio.run(agent.chat("当地有什么风土人情和礼仪？", planned.session_id))
        self.assertEqual(answer.stage, "answering")
        self.assertIn("桂林", answer.reply)

    def test_agent_uses_weather_skill_for_follow_up(self):
        agent = TravelAgent(SessionStore(), SkillLoader(SKILLS_DIR))
        planned = asyncio.run(agent.chat("从广州自驾去桂林，玩4天"))
        with patch("agents.travel_agent.get_travel_weather", new=AsyncMock(return_value="未来四天天气建议")) as weather:
            answer = asyncio.run(agent.chat("这几天天气怎么样？", planned.session_id))
        self.assertEqual(answer.stage, "answering")
        self.assertEqual(answer.reply, "未来四天天气建议")
        weather.assert_awaited_once_with("桂林", 4)

    def test_long_route_recommends_flight(self):
        route = build_map_route("北京", "三亚", "综合推荐")
        self.assertEqual(route.transport, "飞机")

    def test_map_accepts_smaller_city_for_amap_geocoding(self):
        route = build_map_route("景德镇", "阿勒泰", "飞机")
        self.assertEqual(route.origin, "景德镇")
        self.assertEqual(route.destination, "阿勒泰")
        self.assertEqual(route.points[0].longitude, 0)


if __name__ == "__main__":
    unittest.main()
