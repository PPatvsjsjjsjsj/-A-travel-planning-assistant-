import json
import re
import uuid

from fastapi import HTTPException

from config.settings import settings
from core.deepseek_client import create_chat_completion
from messaging.session_store import SessionStore
from models.chat import ChatResponse
from models.trip import TripRequest
from services.request_parser import (
    INTEREST_KEYWORDS,
    has_explicit_days,
    has_explicit_transport,
    parse_natural_request,
)
from services.travel_planner import create_trip_plan
from services.weather import get_travel_weather
from skills.loader import SkillLoader


DESTINATION_CULTURE = {
    "北京": "北京人说话直爽，胡同里的生活节奏比景区慢一拍。进院落、寺庙和博物馆时稍微收着音量，和本地人问路用一句‘您好’开头，通常比举着手机乱转靠谱。",
    "上海": "上海的城市气质是精细和讲究，弄堂、老洋房与咖啡馆挨得很近。排队、预约和地铁换乘都讲秩序，别在高峰期拖着大箱子横穿人群，王哥替你先把尴尬排除了。",
    "西安": "西安人热情爽快，城墙、坊巷和夜市把历史和烟火气揉在一起。回民街尊重清真饮食习惯，别拿食物开玩笑，也别把景区第一家店当成全城水平，往巷子里走两步更容易遇到真味道。",
    "成都": "成都讲究一个松弛，茶馆里坐半天不叫浪费时间，叫本地文化体验。吃辣量力而行，嘴上说‘微辣’不代表胃也同意，王哥建议备点肠胃药，别让辣椒成为旅途中最有存在感的导游。",
    "重庆": "重庆人爽快，山城生活靠步行、坡道和导航共同完成。夜景热闹但坡多路绕，打车看清上车点再走，别被地图上五百米的距离骗了，可能中间还藏着一座山。",
    "桂林": "桂林和阳朔的生活节奏偏慢，漓江边的渔火、米粉和骑行是当地的日常风景。竹筏、游船和包车先看官方价格与码头信息，风景可以慢慢看，临时加价的热情就不用接。",
    "杭州": "杭州人把西湖当日常公园，清晨散步比中午挤在断桥拍照更有味道。灵隐、博物馆和热门展馆常要预约，尊重寺院清静，别把许愿牌写成小作文贴满墙。",
    "广州": "广州的城市性格务实又好吃，早茶不是一杯茶，是一整套慢慢聊、慢慢点的生活方式。点心按人头量力而行，先问清计价方式，别让一笼虾饺把预算变成悬疑片。",
    "苏州": "苏州园林看的是借景、漏窗和曲折动线，慢一点才看得出巧思。平江路和古镇适合早晚逛，遇到穿着古装主动合影或带路的人，先确认是否收费。",
    "青岛": "青岛的海风、啤酒和老城区街巷都很有辨识度。海边注意潮汐和风浪，海鲜餐馆先看明码标价，啤酒可以尝，酒量不要交给海风决定。",
}


class TravelAgent:
    def __init__(self, store: SessionStore, skills: SkillLoader):
        self.store = store
        self.skills = skills

    async def chat(self, message: str, session_id: str | None = None) -> ChatResponse:
        session_id = session_id or uuid.uuid4().hex
        session = self.store.get_or_create(session_id)
        message = message.strip()
        session.add_message("user", message)

        if session.trip_request and session.plan and self._is_travel_question(message) and not self._looks_like_update(message):
            skill_names, skill_context = self.skills.build_context(session.trip_request)
            reply = await self._answer_follow_up(message, session, skill_context)
            session.skills_used = skill_names
            session.add_message("assistant", reply)
            return ChatResponse(
                session_id=session_id,
                reply=reply,
                stage="answering",
                request=session.trip_request,
                skills_used=skill_names,
                quick_replies=["这几天天气怎么样", "当地有什么饮食禁忌", "下雨天怎么调整", "还有哪些避坑"],
            )

        request, updated = self._resolve_request(message, session.trip_request)
        if request is None:
            reply = self._collecting_reply(message, session.trip_request)
            session.add_message("assistant", reply)
            return ChatResponse(
                session_id=session_id,
                reply=reply,
                stage="collecting",
                request=session.trip_request,
                plan=session.plan,
                skills_used=session.skills_used,
                quick_replies=["从上海去成都，5天，2个人", "从北京去杭州，3天，坐高铁", "从广州自驾去桂林，4天"],
            )

        if self._needs_trip_details(message, request, session.trip_request, session.plan):
            session.trip_request = request
            reply = self._clarification_reply(request, message, session.trip_request)
            session.add_message("assistant", reply)
            return ChatResponse(
                session_id=session_id,
                reply=reply,
                stage="collecting",
                request=request,
                plan=session.plan,
                skills_used=session.skills_used,
                quick_replies=["坐高铁，玩5天", "坐飞机，玩4天", "自驾，玩6天"],
            )

        skill_names, skill_context = self.skills.build_context(request)
        plan = await create_trip_plan(request, skill_context)
        session.trip_request = request
        session.plan = plan
        session.skills_used = skill_names
        stage = "updated" if updated else "planned"
        reply = self._planned_reply(request, plan, skill_names)
        session.add_message("assistant", reply)
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            stage=stage,
            plan=plan,
            request=request,
            skills_used=skill_names,
            quick_replies=["改成5天", "预算改成经济", "加上美食和休闲", "我们带老人，不安排爬山"],
        )

    @staticmethod
    def _looks_like_update(message: str) -> bool:
        markers = ("改成", "调整为", "增加", "减少", "换成", "不要安排", "不安排", "加上")
        return any(marker in message for marker in markers)

    @staticmethod
    def _is_travel_question(message: str) -> bool:
        keywords = (
            "天气", "温度", "下雨", "台风", "穿什么", "带什么", "准备什么", "吃什么", "美食", "忌口", "过敏",
            "风俗", "风土人情", "礼仪", "文化", "节庆", "避坑", "安全吗", "怎么走", "怎么去", "交通", "路线",
            "预约", "门票", "酒店", "住宿", "景点", "哪里玩", "老人", "孩子", "亲子", "高反", "防晒", "怎么办",
        )
        question_words = ("吗", "呢", "怎么样", "如何", "为什么", "能不能", "可不可以", "要不要", "告诉我")
        return any(word in message for word in keywords) or any(word in message for word in question_words)

    async def _answer_follow_up(self, message: str, session: object, skill_context: str) -> str:
        request = session.trip_request
        plan = session.plan
        if any(word in message for word in ("天气", "温度", "下雨", "台风", "穿什么", "防晒")):
            return await get_travel_weather(request.destination, request.days)

        if settings.deepseek_enabled:
            try:
                plan_context = json.dumps(plan.model_dump(mode="json"), ensure_ascii=False)
                history = [
                    {"role": item["role"], "content": item["content"]}
                    for item in session.messages[-8:]
                    if item["role"] in {"user", "assistant"}
                ]
                return await create_chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是探山的资深导游王哥。用户已经有旅行计划，现在是在追问旅行过程中的问题。"
                                "请直接回答问题，结合当前行程和提供的技能规则；语气专业、略碎嘴、幽默但不油腻。"
                                "不确定的实时信息要明确说明，不得编造天气、票务、营业时间或预警。\n\n" + skill_context
                            ),
                        },
                        {"role": "system", "content": "当前旅行计划：" + plan_context[:12000]},
                        *history,
                    ],
                    temperature=0.65,
                    max_tokens=1400,
                )
            except Exception:
                pass
        return self._local_follow_up(message, request, plan)

    @staticmethod
    def _local_follow_up(message: str, request: TripRequest, plan: object) -> str:
        if any(word in message for word in ("吃什么", "美食", "忌口", "过敏")):
            meals = list(dict.fromkeys(meal for day in plan.itinerary for meal in day.meals))[:4]
            return f"王哥给你把嘴这件大事先照顾上：{'；'.join(meals)}。有过敏或忌口就提前说，别到了饭桌上才和花生、海鲜临时谈判。"
        if any(word in message for word in ("风俗", "风土人情", "礼仪", "文化", "节庆")):
            culture = DESTINATION_CULTURE.get(request.destination, f"到{request.destination}先尊重当地生活节奏，进宗教场所和村寨按现场礼仪来。")
            return f"说到{request.destination}的风土人情，王哥得多唠两句：{culture}"
        if any(word in message for word in ("交通", "路线", "怎么走", "怎么去")):
            option = plan.transport_options[0]
            return f"这段路按{option.mode}走：{option.route}，常规{option.duration}。{'；'.join(option.steps)}。别把换乘时间压得像考试最后五分钟，留点余量人会舒服很多。"
        if any(word in message for word in ("带什么", "准备什么", "老人", "孩子", "高反", "防晒")):
            prep = plan.preparation
            items = (prep.essentials + prep.health + prep.destination_specific)[:8]
            return f"准备清单王哥替你压缩成重点：{'、'.join(items)}。证件和常用药放随身包，别托运，行李箱丢了还能玩，人别跟着行李一起慌。"
        if any(word in message for word in ("预算", "花费", "多少钱", "省钱")):
            return f"当前落地预算是{plan.budget.total}。住宿{plan.budget.accommodation}，餐饮{plan.budget.food}，门票{plan.budget.tickets}。先守住住宿和交通，伴手礼别一激动买成批发。"
        if any(word in message for word in ("酒店", "住宿", "住哪里")):
            stays = list(dict.fromkeys(day.accommodation for day in plan.itinerary if day.accommodation))[:3]
            return f"住宿王哥建议这样选：{'；'.join(stays)}。优先看夜间返程、地铁距离和隔音，网红浴缸拍完照不能替你睡个好觉。"
        if any(word in message for word in ("预约", "门票", "营业时间")):
            return f"预约顺序按这个来：{'；'.join(plan.booking_tips)}。实时余票和开放时间会变，临出发前再查官方渠道，别让黄牛比景点先接待你。"
        if any(word in message for word in ("避坑", "安全吗", "安全")):
            return f"王哥的避坑清单：{'；'.join(plan.practical_tips)}。凡是主动拉客、价格含糊、催你立刻付款的，先慢三秒，旅行里最值钱的技能有时就是不着急。"
        if any(word in message for word in ("景点", "哪里玩", "下雨", "怎么办")):
            days = "；".join(f"第{day.day}天{day.title}" for day in plan.itinerary[:5])
            return f"当前安排是：{days}。你告诉王哥想改哪一天或遇到什么情况，我可以按同片区替换，尽量不让你拖着腿满城折返。"
        return f"这事和{request.destination}行程有关，王哥能接着答。你可以问天气、路线、美食、风俗、准备、预算、住宿或避坑，问题说具体一点，我就不拿套话糊弄你。"

    @staticmethod
    def _needs_trip_details(
        message: str,
        request: TripRequest,
        previous: TripRequest | None,
        existing_plan: object | None,
    ) -> bool:
        # A completed trip can be edited without being forced through the intake questions again.
        if existing_plan is not None:
            return False
        history = previous.notes if previous else ""
        has_days = has_explicit_days(message) or has_explicit_days(history)
        # A stated duration is enough to start with the distance-based recommendation.
        # The truly vague "西安去北京" style request has no duration and stays in intake.
        has_transport = has_explicit_transport(message) or has_explicit_transport(history)
        return not has_days

    @staticmethod
    def _clarification_reply(request: TripRequest, message: str, previous: TripRequest | None) -> str:
        history = previous.notes if previous else ""
        missing_days = not (has_explicit_days(message) or has_explicit_days(history))
        missing_transport = not (has_explicit_transport(message) or has_explicit_transport(history))
        missing = []
        if missing_transport:
            missing.append("交通方式")
        if missing_days:
            missing.append("玩几天")
        if missing_transport and missing_days:
            question = "你更想坐高铁、飞机，还是自驾？顺手告诉王哥准备玩几天。"
            recommendation = "西安到北京这种距离，高铁是市中心到市中心，省掉机场折腾；赶时间就选飞机，自驾适合把沿途风景也吃进计划里。"
        elif missing_transport:
            question = "天数记下了，交通还没定。你想坐高铁、飞机、火车，还是自驾？"
            recommendation = "王哥先给你个判断：两地市中心往返优先高铁，时间特别紧选飞机，想边走边玩再自驾。"
        else:
            question = "交通记下了，还差玩几天。你准备在目的地住几晚？"
            recommendation = "别把每天塞成赶集，王哥建议至少留一整天给核心景点，再给返程留出缓冲。"
        return (
            f"收到，{request.origin}到{request.destination}这条线王哥先替你占上了。"
            f"不过{'、'.join(missing)}还没说死，{question}\n\n{recommendation}"
        )

    @staticmethod
    def _planned_reply(request: TripRequest, plan: object, skill_names: list[str]) -> str:
        transport = plan.transport_options[0] if plan.transport_options else None
        transport_line = f"{transport.mode}：{transport.route}，{transport.duration}。" if transport else "交通方式已按距离和偏好安排。"
        day_lines = []
        for day in plan.itinerary[: min(6, len(plan.itinerary))]:
            highlights = "、".join(item.activity for item in day.schedule[:2])
            day_lines.append(f"第{day.day}天，{day.title}。重点是{highlights}。")
        if len(plan.itinerary) > 6:
            day_lines.append(f"后面还有{len(plan.itinerary) - 6}天，王哥按同片区慢慢铺开，避免来回折返。")
        preparation = plan.preparation
        prep = "、".join((preparation.essentials + preparation.destination_specific)[:5])
        local = "；".join(plan.practical_tips[:3])
        culture = DESTINATION_CULTURE.get(
            request.destination,
            f"{request.destination}的风土人情要靠慢下来观察：先尊重当地生活节奏，再尝代表性食物，进场馆和宗教场所按当地规矩来。",
        )
        return (
            f"行，王哥给你捋完了：{request.origin}出发，去{request.destination}，{request.days}天，{request.travelers}个人，{request.budget_level}档。\n\n"
            f"怎么去：{transport_line}{transport.advice if transport else ''}\n\n"
            f"怎么玩：{' '.join(day_lines)}\n\n"
            f"出发前准备：{prep}。重点预约、证件和天气提醒都已经放进旅游准备板块，别到了门口才翻手机找二维码。\n\n"
            f"当地风土人情：{culture}\n\n"
            f"当地特色和避坑：{local}\n\n"
            f"这次王哥调用了{len(skill_names)}项旅行技能。路线、天数、交通和口味哪里想改，直接说，王哥继续给你掰开揉碎安排。"
        )

    def _resolve_request(self, message: str, previous: TripRequest | None) -> tuple[TripRequest | None, bool]:
        try:
            return parse_natural_request(message), previous is not None
        except (HTTPException, ValueError):
            pass

        if previous is None:
            return None, False

        updates = {}
        days = re.search(r"(?:改成|调整为|玩|安排)?\s*(\d{1,2})\s*(?:天|日)", message)
        travelers = re.search(r"(?:改成|一共|我们)?\s*(\d{1,2})\s*(?:个?人|位)", message)
        budget = re.search(r"(?:预算)?(?:改成|调整为|要)?\s*(经济|舒适|品质)", message)
        if days:
            updates["days"] = int(days.group(1))
        if travelers:
            updates["travelers"] = int(travelers.group(1))
        if budget:
            updates["budget_level"] = budget.group(1)

        transport = next((item for item in ("高铁", "飞机", "自驾", "火车") if item in message), None)
        if transport:
            updates["transport_preference"] = transport

        interests = list(previous.interests)
        for label, words in INTEREST_KEYWORDS.items():
            if any(word in message for word in words) and label not in interests:
                interests.append(label)
        if interests != previous.interests:
            updates["interests"] = interests

        note_markers = ("老人", "儿童", "轮椅", "过敏", "忌口", "不安排", "不要", "节庆", "民族")
        if any(marker in message for marker in note_markers):
            updates["notes"] = (previous.notes + "；" + message).strip("；")

        if not updates:
            return None, False
        return previous.model_copy(update=updates), True

    @staticmethod
    def _collecting_reply(message: str, previous: TripRequest | None) -> str:
        if previous:
            return "我记得当前行程。请直接告诉我想改的内容，例如“改成5天”“预算改成经济”或“加上亲子体验”。"
        if any(word in message.lower() for word in ("你好", "hello", "hi", "在吗")):
            return "嗨，我是王哥，专门给你捋旅行路线的。出发地、目的地、玩几天先报上来，别让我猜，猜错了还得重排。"
        return "我还需要出发地和目的地。可以直接说：从杭州去西安，玩4天，2个人，喜欢历史和美食。"
