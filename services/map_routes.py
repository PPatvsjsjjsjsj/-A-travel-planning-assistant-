import math

from fastapi import HTTPException

from models.map import MapPoint, MapRouteResponse


CITY_COORDINATES = {
    "北京": (116.41, 39.90), "天津": (117.20, 39.13), "石家庄": (114.51, 38.04),
    "太原": (112.55, 37.87), "呼和浩特": (111.75, 40.84), "沈阳": (123.43, 41.80),
    "大连": (121.61, 38.91), "长春": (125.32, 43.82), "哈尔滨": (126.53, 45.80),
    "上海": (121.47, 31.23), "南京": (118.80, 32.06), "苏州": (120.59, 31.30),
    "杭州": (120.15, 30.27), "宁波": (121.55, 29.87), "合肥": (117.23, 31.82),
    "福州": (119.30, 26.08), "厦门": (118.09, 24.48), "南昌": (115.86, 28.68),
    "济南": (117.12, 36.65), "青岛": (120.38, 36.07), "郑州": (113.62, 34.75),
    "武汉": (114.31, 30.59), "长沙": (112.94, 28.23), "广州": (113.26, 23.13),
    "深圳": (114.06, 22.54), "珠海": (113.58, 22.27), "南宁": (108.37, 22.82),
    "桂林": (110.29, 25.27), "海口": (110.20, 20.04), "三亚": (109.51, 18.25),
    "重庆": (106.55, 29.56), "成都": (104.07, 30.57), "贵阳": (106.63, 26.65),
    "昆明": (102.83, 25.04), "拉萨": (91.11, 29.65), "西安": (108.94, 34.34),
    "兰州": (103.83, 36.06), "西宁": (101.78, 36.62), "银川": (106.23, 38.49),
    "乌鲁木齐": (87.62, 43.82), "张家界": (110.48, 29.13), "洛阳": (112.45, 34.62),
    "开封": (114.31, 34.80), "秦皇岛": (119.60, 39.94), "烟台": (121.45, 37.46),
    "无锡": (120.31, 31.49), "温州": (120.70, 28.00), "泉州": (118.68, 24.87),
    "大理": (100.23, 25.59), "丽江": (100.23, 26.87), "敦煌": (94.66, 40.14),
    "肇庆": (112.47, 23.05), "贺州": (111.57, 24.40), "阳朔": (110.49, 24.78),
    "临汾": (111.52, 36.09), "徐州": (117.28, 34.20), "宜昌": (111.29, 30.69),
}

ROAD_CORRIDORS = {
    ("广州", "桂林"): ["肇庆", "贺州", "阳朔"],
    ("北京", "上海"): ["天津", "济南", "徐州", "南京"],
    ("西安", "北京"): ["临汾", "太原", "石家庄"],
    ("上海", "成都"): ["南京", "武汉", "宜昌", "重庆"],
    ("广州", "成都"): ["桂林", "贵阳", "重庆"],
    ("北京", "杭州"): ["济南", "徐州", "南京"],
}

# Public hub names used by the web map so each mode lands on a real station or airport.
CITY_HUBS = {
    "北京": {"高铁": "北京南站", "火车": "北京站", "飞机": "北京首都国际机场"},
    "上海": {"高铁": "上海虹桥站", "火车": "上海站", "飞机": "上海虹桥国际机场"},
    "广州": {"高铁": "广州南站", "火车": "广州站", "飞机": "广州白云国际机场"},
    "深圳": {"高铁": "深圳北站", "火车": "深圳站", "飞机": "深圳宝安国际机场"},
    "杭州": {"高铁": "杭州东站", "火车": "杭州站", "飞机": "杭州萧山国际机场"},
    "南京": {"高铁": "南京南站", "火车": "南京站", "飞机": "南京禄口国际机场"},
    "西安": {"高铁": "西安北站", "火车": "西安站", "飞机": "西安咸阳国际机场"},
    "成都": {"高铁": "成都东站", "火车": "成都站", "飞机": "成都天府国际机场"},
    "重庆": {"高铁": "重庆北站", "火车": "重庆站", "飞机": "重庆江北国际机场"},
    "武汉": {"高铁": "武汉站", "火车": "武昌站", "飞机": "武汉天河国际机场"},
    "长沙": {"高铁": "长沙南站", "火车": "长沙站", "飞机": "长沙黄花国际机场"},
    "郑州": {"高铁": "郑州东站", "火车": "郑州站", "飞机": "郑州新郑国际机场"},
    "济南": {"高铁": "济南西站", "火车": "济南站", "飞机": "济南遥墙国际机场"},
    "青岛": {"高铁": "青岛北站", "火车": "青岛站", "飞机": "青岛胶东国际机场"},
    "厦门": {"高铁": "厦门北站", "火车": "厦门站", "飞机": "厦门高崎国际机场"},
    "昆明": {"高铁": "昆明南站", "火车": "昆明站", "飞机": "昆明长水国际机场"},
    "桂林": {"高铁": "桂林北站", "火车": "桂林站", "飞机": "桂林两江国际机场"},
    "三亚": {"高铁": "三亚站", "火车": "三亚站", "飞机": "三亚凤凰国际机场"},
}

def build_map_route(origin: str, destination: str, transport: str = "综合推荐") -> MapRouteResponse:
    origin_name = resolve_city(origin)
    destination_name = resolve_city(destination)
    if origin_name == destination_name:
        raise HTTPException(status_code=422, detail="地图路线的出发地和目的地不能相同")

    if origin_name not in CITY_COORDINATES or destination_name not in CITY_COORDINATES:
        mode = normalize_transport(transport, 1000)
        points = [
            MapPoint(name=origin_name, longitude=0, latitude=0, kind="origin"),
            MapPoint(name=destination_name, longitude=0, latitude=0, kind="destination"),
        ]
        return MapRouteResponse(
            origin=origin_name,
            destination=destination_name,
            transport=mode,
            distance_km=0,
            duration="打开高德地图后计算",
            description=f"{origin_name}至{destination_name}的{mode}路线，由高德地理编码定位城市。",
            points=points,
        )

    start = CITY_COORDINATES[origin_name]
    end = CITY_COORDINATES[destination_name]
    direct_distance = haversine(start[1], start[0], end[1], end[0])
    mode = normalize_transport(transport, direct_distance)
    hub_names = _route_hubs(origin_name, destination_name, mode)
    names = [origin_name, *_road_corridor(origin_name, destination_name), destination_name] if mode == "自驾" else hub_names
    points = []
    for index, name in enumerate(names):
        coordinates = CITY_COORDINATES[name] if mode == "自驾" else (start if index == 0 else end)
        points.append(MapPoint(
            name=name,
            longitude=coordinates[0],
            latitude=coordinates[1],
            kind="origin" if index == 0 else "destination" if index == len(names) - 1 else "waypoint",
        ))

    multiplier = {"飞机": 1.0, "高铁": 1.10, "自驾": 1.18, "火车": 1.13}[mode]
    distance = max(1, round(direct_distance * multiplier))
    duration = estimate_duration(distance, mode)
    if mode == "自驾":
        description = f"{origin_name}市区至{destination_name}市区的驾车路线由高德道路规划实时绘制。"
    else:
        departure, arrival = hub_names
        description = f"地图定位{departure}至{arrival}，按{mode}展示两地真实交通枢纽走向。"

    return MapRouteResponse(
        origin=origin_name,
        destination=destination_name,
        transport=mode,
        distance_km=distance,
        duration=duration,
        description=description,
        points=points,
    )


def _route_hubs(origin: str, destination: str, mode: str) -> list[str]:
    if mode == "自驾":
        return []
    default_suffix = "机场" if mode == "飞机" else "站"
    origin_hub = CITY_HUBS.get(origin, {}).get(mode, f"{origin}{default_suffix}")
    destination_hub = CITY_HUBS.get(destination, {}).get(mode, f"{destination}{default_suffix}")
    return [origin_hub, destination_hub]


def _road_corridor(origin: str, destination: str) -> list[str]:
    direct = ROAD_CORRIDORS.get((origin, destination))
    if direct is not None:
        return direct
    reverse = ROAD_CORRIDORS.get((destination, origin))
    return list(reversed(reverse)) if reverse else []


def resolve_city(value: str) -> str:
    cleaned = value.strip()
    for suffix in ("特别行政区", "自治区", "自治州", "地区", "省", "市"):
        cleaned = cleaned.removesuffix(suffix)
    if cleaned in CITY_COORDINATES:
        return cleaned
    matches = [name for name in CITY_COORDINATES if name in cleaned or cleaned in name]
    if matches:
        return min(matches, key=len)
    return cleaned or value.strip()


def normalize_transport(value: str, distance: float) -> str:
    for mode in ("高铁", "飞机", "自驾", "火车"):
        if mode in value:
            return mode
    return "飞机" if distance > 1400 else "高铁"


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def estimate_duration(distance: int, mode: str) -> str:
    if mode == "飞机":
        hours = distance / 750 + 2.0
    elif mode == "高铁":
        hours = distance / 260 + 0.6
    elif mode == "火车":
        hours = distance / 110 + 0.8
    else:
        hours = distance / 85 + max(0.5, distance / 600)
    if hours < 10:
        return f"约{hours:.1f}小时"
    return f"约{round(hours)}小时"
