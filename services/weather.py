import asyncio
import json
import urllib.parse
import urllib.request
from datetime import date

from services.map_routes import CITY_COORDINATES, resolve_city


WEATHER_CODES = {
    0: "晴", 1: "大部晴朗", 2: "多云", 3: "阴",
    45: "有雾", 48: "雾凇", 51: "小毛毛雨", 53: "毛毛雨", 55: "较强毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "较强阵雨", 82: "强阵雨", 95: "雷雨", 96: "雷雨伴冰雹", 99: "强雷雨伴冰雹",
}


async def get_travel_weather(city: str, days: int) -> str:
    city_name = resolve_city(city)
    coordinates = CITY_COORDINATES.get(city_name)
    if not coordinates:
        return _seasonal_fallback(city_name, "没有找到该城市的天气坐标")
    try:
        payload = await asyncio.to_thread(_fetch_forecast, coordinates, days)
        daily = payload["daily"]
        rows = []
        for index, day in enumerate(daily["time"]):
            weather = WEATHER_CODES.get(daily["weather_code"][index], "天气变化")
            low = round(daily["temperature_2m_min"][index])
            high = round(daily["temperature_2m_max"][index])
            rain = round(daily["precipitation_probability_max"][index] or 0)
            wind = round(daily["wind_speed_10m_max"][index] or 0)
            rows.append(f"{day}：{weather}，{low}-{high}℃，降水概率{rain}%、最大风速约{wind}km/h")
        advice = _weather_advice(daily)
        return (
            f"王哥查到{city_name}未来{len(rows)}天预报：\n"
            + "\n".join(rows)
            + f"\n\n{advice}。数据来自 Open-Meteo 实时预报；临出发前再查看中国气象部门预警，别让一场阵雨临时当领队。"
        )
    except Exception as exc:
        return _seasonal_fallback(city_name, type(exc).__name__)


def _fetch_forecast(coordinates: tuple[float, float], days: int) -> dict:
    longitude, latitude = coordinates
    query = urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        "timezone": "Asia/Shanghai",
        "forecast_days": max(1, min(int(days), 7)),
    })
    request = urllib.request.Request(
        f"https://api.open-meteo.com/v1/forecast?{query}",
        headers={"User-Agent": "TanshanTravel/1.0"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _weather_advice(daily: dict) -> str:
    rain = max(daily.get("precipitation_probability_max") or [0])
    high = max(daily.get("temperature_2m_max") or [25])
    low = min(daily.get("temperature_2m_min") or [18])
    advice = []
    if rain >= 45:
        advice.append("带折叠伞和防水鞋袋，漓江、登山等户外项目预留室内替代")
    if high >= 32:
        advice.append("午后减少暴晒，准备防晒、补水和电解质饮品")
    if low <= 12:
        advice.append("早晚温差明显，带一件轻便保暖外套")
    if not advice:
        advice.append("带轻薄外套和便携雨具，按早晚温差调整穿着")
    return "；".join(advice)


def _seasonal_fallback(city: str, reason: str) -> str:
    month = date.today().month
    if month in (6, 7, 8):
        season = "当前处于夏季，通常闷热多阵雨，准备透气衣物、防晒、雨具和补水用品"
    elif month in (12, 1, 2):
        season = "当前处于冬季，早晚偏冷，准备分层保暖、防风外套和防滑鞋"
    else:
        season = "当前处于换季阶段，昼夜温差可能较大，准备可增减的外套和便携雨具"
    return (
        f"王哥暂时没拿到{city}的实时天气数据（{reason}），下面只能当季节准备，不能冒充实时预报：{season}。"
        "出发前查看中国气象部门预报和预警，户外行程至少留一个博物馆或室内街区作为替代。"
    )
