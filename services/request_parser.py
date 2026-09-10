import re

from fastapi import HTTPException

from models.trip import TripRequest


INTEREST_KEYWORDS = {
    "历史": ("历史", "古迹", "博物馆", "人文"),
    "美食": ("美食", "吃", "小吃", "夜市"),
    "自然": ("自然", "山水", "风景", "徒步", "爬山"),
    "摄影": ("摄影", "拍照", "出片"),
    "亲子": ("亲子", "孩子", "儿童"),
    "休闲": ("休闲", "轻松", "慢游", "不赶"),
}


def parse_natural_request(message: str) -> TripRequest:
    text = re.sub(r"\s+", "", message.strip())
    route_patterns = (
        r"从(?P<origin>[\u4e00-\u9fa5A-Za-z]{2,20}?)(?:(?:坐|乘|搭)(?:高铁|飞机|火车|汽车)|自驾)?(?:去|到)(?P<destination>[\u4e00-\u9fa5A-Za-z]{2,20}?)(?=玩|旅游|旅行|出发|自驾|坐|乘|搭|，|,|。|\d|$)",
        r"(?P<origin>[\u4e00-\u9fa5A-Za-z]{2,12}?)出发(?:(?:坐|乘|搭)(?:高铁|飞机|火车|汽车)|自驾)?(?:去|到)(?P<destination>[\u4e00-\u9fa5A-Za-z]{2,12}?)(?=玩|旅游|旅行|，|,|。|\d|$)",
        r"(?P<origin>[\u4e00-\u9fa5A-Za-z]{2,12}?)(?:坐|乘|搭)?(?:高铁|飞机|火车|汽车|自驾)?(?:去|到)(?P<destination>[\u4e00-\u9fa5A-Za-z]{2,12}?)(?=玩|旅游|旅行|出发|，|,|。|\d|$)",
    )

    match = None
    for pattern in route_patterns:
        match = re.search(pattern, text)
        if match:
            break
    if not match:
        raise HTTPException(
            status_code=422,
            detail="请说明出发地和目的地，例如：从杭州去西安，玩4天。",
        )

    origin = _clean_place(match.group("origin"))
    destination = _clean_place(match.group("destination"))
    days_match = re.search(r"(\d{1,2})\s*(?:天|日)", text)
    travelers_match = re.search(r"(\d{1,2})\s*(?:个?人|位)", text)

    if "经济" in text or "省钱" in text or "穷游" in text:
        budget = "经济"
    elif "品质" in text or "豪华" in text or "高端" in text:
        budget = "品质"
    else:
        budget = "舒适"

    transport = next((item for item in ("高铁", "飞机", "自驾", "火车") if item in text), "综合推荐")
    interests = [label for label, words in INTEREST_KEYWORDS.items() if any(word in text for word in words)]

    notes = text
    return TripRequest(
        origin=origin,
        destination=destination,
        days=int(days_match.group(1)) if days_match else 3,
        travelers=int(travelers_match.group(1)) if travelers_match else 1,
        budget_level=budget,
        transport_preference=transport,
        interests=interests,
        notes=notes,
    )


def has_explicit_days(message: str) -> bool:
    """Return whether the traveler gave a concrete stay length."""
    return bool(re.search(r"\d{1,2}\s*(?:天|日)", re.sub(r"\s+", "", message or "")))


def has_explicit_transport(message: str) -> bool:
    """Return whether a transport mode was named instead of inferred."""
    text = re.sub(r"\s+", "", message or "")
    return any(mode in text for mode in ("高铁", "飞机", "自驾", "火车"))


def _clean_place(value: str) -> str:
    value = re.sub(r"^(我想|我要|计划|准备|打算)", "", value)
    value = re.sub(r"(市|省)$", "", value)
    return value.strip()
