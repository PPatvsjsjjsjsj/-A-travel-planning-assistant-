import logging

from config.settings import settings
from core.deepseek_client import create_chat_completion, extract_json_object
from models.trip import TripPlan, TripRequest
from prompts.travel import SYSTEM_PROMPT, build_user_prompt
from services.local_planner import build_local_plan


logger = logging.getLogger(__name__)


async def create_trip_plan(request: TripRequest, skill_context: str = "") -> TripPlan:
    if not settings.deepseek_enabled:
        return build_local_plan(request)

    try:
        system_prompt = SYSTEM_PROMPT
        if skill_context:
            system_prompt += "\n\n以下是本次行程必须遵循的专业技能规则：\n" + skill_context
        content = await create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_user_prompt(request)},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=8000,
        )
        payload = extract_json_object(content)
        payload["source"] = "deepseek"
        plan = TripPlan.model_validate(payload)
        if len(plan.itinerary) != request.days:
            raise ValueError("DeepSeek 返回的每日计划数量与旅行天数不一致")
        return plan
    except Exception as exc:
        logger.exception("DeepSeek planning failed; falling back to local plan")
        plan = build_local_plan(request)
        plan.notice = f"DeepSeek 暂时不可用，已返回本地演示规划。原因：{type(exc).__name__}。交通、票价和开放信息请以官方渠道为准。"
        return plan
