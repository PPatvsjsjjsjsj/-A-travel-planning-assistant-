import math

from models.trip import (
    BudgetSummary,
    DayPlan,
    ScheduleItem,
    TransportOption,
    TravelPreparation,
    TripPlan,
    TripRequest,
)
from services.map_routes import build_map_route


DESTINATION_GUIDES = {
    "北京": ["故宫博物院、景山公园", "天坛公园、前门大街", "八达岭长城", "颐和园、圆明园", "国家博物馆、什刹海"],
    "上海": ["外滩、南京东路", "豫园、老城厢", "武康路、徐家汇", "陆家嘴、浦东美术馆", "朱家角古镇"],
    "西安": ["西安城墙、钟鼓楼", "秦始皇帝陵博物院", "陕西历史博物馆、大雁塔", "华清宫、骊山", "碑林博物馆、书院门"],
    "成都": ["人民公园、宽窄巷子", "成都大熊猫繁育研究基地", "武侯祠、锦里", "都江堰景区", "青城山"],
    "杭州": ["断桥、孤山、曲院风荷", "灵隐飞来峰", "西溪国家湿地公园", "良渚博物院", "小河直街、京杭大运河"],
    "南京": ["中山陵、明孝陵", "南京博物院", "总统府、六朝博物馆", "夫子庙、老门东", "玄武湖、南京城墙"],
    "重庆": ["解放碑、洪崖洞", "李子坝、鹅岭二厂", "磁器口、渣滓洞", "武隆天生三桥", "长江索道、南山一棵树"],
    "厦门": ["鼓浪屿", "南普陀寺、厦门大学外部街区", "环岛路、曾厝垵", "集美学村", "沙坡尾、八市"],
    "广州": ["陈家祠、荔枝湾", "沙面、永庆坊", "广东省博物馆、花城广场", "白云山", "北京路、珠江夜游"],
    "苏州": ["拙政园、苏州博物馆", "平江路历史街区", "虎丘、山塘街", "金鸡湖", "同里古镇"],
    "桂林": ["象鼻山、两江四湖", "漓江游船、阳朔", "遇龙河、十里画廊", "龙脊梯田", "靖江王城、东西巷"],
    "张家界": ["张家界国家森林公园", "袁家界、天子山", "金鞭溪、十里画廊", "天门山国家森林公园", "大峡谷玻璃桥"],
    "大理": ["大理古城、崇圣寺三塔", "洱海生态廊道", "喜洲古镇", "苍山感通索道", "双廊、挖色"],
    "丽江": ["丽江古城、黑龙潭", "玉龙雪山、蓝月谷", "束河古镇", "白沙古镇", "拉市海"],
    "青岛": ["栈桥、大学路", "八大关、第二海水浴场", "崂山太清游览区", "青岛啤酒博物馆", "小麦岛、奥帆中心"],
}


CITY_HUBS = {
    "北京": ("北京南站", "北京大兴国际机场"), "上海": ("上海虹桥站", "上海虹桥国际机场"),
    "广州": ("广州南站", "广州白云国际机场"), "深圳": ("深圳北站", "深圳宝安国际机场"),
    "杭州": ("杭州东站", "杭州萧山国际机场"), "南京": ("南京南站", "南京禄口国际机场"),
    "苏州": ("苏州站", "上海虹桥国际机场"), "西安": ("西安北站", "西安咸阳国际机场"),
    "成都": ("成都东站", "成都天府国际机场"), "重庆": ("重庆北站", "重庆江北国际机场"),
    "武汉": ("武汉站", "武汉天河国际机场"), "长沙": ("长沙南站", "长沙黄花国际机场"),
    "郑州": ("郑州东站", "郑州新郑国际机场"), "济南": ("济南西站", "济南遥墙国际机场"),
    "青岛": ("青岛北站", "青岛胶东国际机场"), "厦门": ("厦门站", "厦门高崎国际机场"),
    "福州": ("福州站", "福州长乐国际机场"), "南昌": ("南昌西站", "南昌昌北国际机场"),
    "合肥": ("合肥南站", "合肥新桥国际机场"), "昆明": ("昆明南站", "昆明长水国际机场"),
    "贵阳": ("贵阳北站", "贵阳龙洞堡国际机场"), "南宁": ("南宁东站", "南宁吴圩国际机场"),
    "桂林": ("桂林北站", "桂林两江国际机场"), "大理": ("大理站", "大理凤仪机场"),
    "丽江": ("丽江站", "丽江三义国际机场"), "三亚": ("三亚站", "三亚凤凰国际机场"),
    "海口": ("海口东站", "海口美兰国际机场"), "沈阳": ("沈阳北站", "沈阳桃仙国际机场"),
    "大连": ("大连北站", "大连周水子国际机场"), "长春": ("长春西站", "长春龙嘉国际机场"),
    "哈尔滨": ("哈尔滨西站", "哈尔滨太平国际机场"), "天津": ("天津站", "天津滨海国际机场"),
    "石家庄": ("石家庄站", "石家庄正定国际机场"), "太原": ("太原南站", "太原武宿国际机场"),
    "兰州": ("兰州西站", "兰州中川国际机场"), "西宁": ("西宁站", "西宁曹家堡国际机场"),
    "银川": ("银川站", "银川河东国际机场"), "乌鲁木齐": ("乌鲁木齐站", "乌鲁木齐天山国际机场"),
    "拉萨": ("拉萨站", "拉萨贡嘎国际机场"), "张家界": ("张家界西站", "张家界荷花国际机场"),
}


def build_local_plan(request: TripRequest) -> TripPlan:
    spots = DESTINATION_GUIDES.get(request.destination, [
        f"{request.destination}核心历史街区",
        f"{request.destination}代表性博物馆",
        f"{request.destination}城市公园与地标",
        f"{request.destination}本地生活街区",
        f"{request.destination}近郊代表性景区",
    ])
    day_plans = _build_days(request, spots)
    budget = _build_budget(request)
    route = _build_transport(request)
    return TripPlan(
        title=f"{request.origin}出发 · {request.destination}{request.days}日旅行计划",
        summary=f"以{request.destination}相邻片区为单位安排每日动线，首尾两天保留进出城时间。交通卡片给出实际枢纽与换乘顺序，不展示票价。",
        origin=request.origin,
        destination=request.destination,
        days=request.days,
        best_for=request.interests or ["首次到访", "经典路线", request.budget_level],
        transport_options=[route],
        itinerary=day_plans,
        budget=budget,
        preparation=_build_preparation(request),
        booking_tips=[
            f"先预约{request.destination}需要实名或分时入园的博物馆与热门景区，再锁定住宿。",
            "把住宿选在首日抵达枢纽可直达、且靠近主要景点片区的轨道交通站点附近。",
            "将门票预约二维码、酒店地址和返程信息离线截图，同行人各保存一份。",
        ],
        practical_tips=[
            "每天只跨一个主要片区，景点之间优先步行或乘坐公共交通，减少折返。",
            "景区门口的低价一日游、无明码标价餐馆和主动搭讪带路服务先核验资质与价格。",
            "出发前 48 小时查看目的地天气；若遇极端天气，优先调整户外项目而不是压缩交通缓冲。",
        ],
        source="local_demo",
    )


def _build_transport(request: TripRequest) -> TransportOption:
    route_data = build_map_route(request.origin, request.destination, request.transport_preference)
    mode = route_data.transport
    origin_train, origin_airport = CITY_HUBS.get(request.origin, (f"{request.origin}站", f"{request.origin}机场"))
    destination_train, destination_airport = CITY_HUBS.get(request.destination, (f"{request.destination}站", f"{request.destination}机场"))
    if mode == "飞机":
        return TransportOption(
            mode="飞机",
            route=f"{origin_airport} → {destination_airport}",
            duration=route_data.duration,
            departure=origin_airport,
            arrival=destination_airport,
            steps=[
                f"从{request.origin}市区前往{origin_airport}，国内航班建议按起飞前约2小时到达航站楼安排时间。",
                f"乘机抵达{destination_airport}，按高德地图的公共交通或驾车路线前往住宿区域。",
                f"返程按相同枢纽反向安排，并把市区到机场的拥堵时间计入缓冲。",
            ],
            advice="两地距离较长时优先飞机；行李多或同行有老人儿童时减少中转。",
        )
    if mode == "自驾":
        return TransportOption(
            mode="自驾",
            route=f"{request.origin}市区 → 高德驾车路线 → {request.destination}住宿区域",
            duration=route_data.duration,
            departure=f"{request.origin}市区",
            arrival=f"{request.destination}住宿区域",
            steps=[
                "在地图板块选择“自驾”，由高德按当前道路与路况绘制实际行驶路线。",
                "每连续驾驶约2小时进入服务区休息，单日长途不要把景点安排在抵达前。",
                f"进入{request.destination}前确认住宿停车条件、景区停车场入口和当地限行规则。",
            ],
            advice="实际道路、拥堵和封闭信息以地图板块实时结果为准，避免疲劳驾驶。",
        )
    label = "普通火车" if mode == "火车" else "高铁"
    route_text = f"{origin_train} → {destination_train}"
    return TransportOption(
        mode=label,
        route=route_text,
        duration=route_data.duration,
        departure=origin_train,
        arrival=destination_train,
        steps=[
            f"从{request.origin}市区前往{origin_train}，按发车时间提前约45分钟抵达进站口。",
            f"从{origin_train}乘{label}前往{destination_train}；若需要换乘，优先选择同站换乘且预留45分钟以上。",
            f"抵达{destination_train}后，打开地图板块规划到住宿区域的公共交通或驾车路线。",
        ],
        advice="选择白天抵达的班次，首日可直接入住并在住宿地附近活动。",
    )


def _build_days(request: TripRequest, spots: list[str]) -> list[DayPlan]:
    budget_levels = {"经济": (90, 160), "舒适": (160, 280), "品质": (300, 520)}
    daily_low, daily_high = budget_levels[request.budget_level]
    plans = []
    for index in range(request.days):
        spot = spots[index % len(spots)]
        if index == 0:
            schedule = [
                ScheduleItem(time="抵达后", activity="从交通枢纽前往住宿并寄存行李", location="住宿区域", tips="先完成入住，再开始市内游览"),
                ScheduleItem(time="15:30", activity=f"游览{spot}", location=spot, tips="首日只安排同片区项目"),
                ScheduleItem(time="18:30", activity="在本地生活街区用晚餐", location=f"{spot}周边", tips="选择明码标价且近期评价稳定的餐馆"),
            ]
            title = f"抵达{request.destination}与城市初识"
        elif index == request.days - 1:
            schedule = [
                ScheduleItem(time="09:00", activity=f"游览{spot}", location=spot, tips="退房后把行李寄存在酒店或正规寄存点"),
                ScheduleItem(time="12:00", activity="午餐与少量伴手礼采购", location=f"{spot}周边", tips="不购买难以携带的液体和生鲜"),
                ScheduleItem(time="返程前", activity="前往返程交通枢纽", location="车站或机场", tips="按交通卡片中的提前量出发"),
            ]
            title = "半日慢游与返程"
        else:
            schedule = [
                ScheduleItem(time="09:00", activity=f"深度游览{spot}", location=spot, tips="需要预约的场馆按预约时段到达"),
                ScheduleItem(time="12:30", activity="品尝目的地代表性午餐", location=f"{spot}周边", tips="避开景区出口第一排揽客餐馆"),
                ScheduleItem(time="14:30", activity="步行串联附近街区、公园或展馆", location=f"{spot}相邻片区", tips="控制在30分钟通勤范围内"),
                ScheduleItem(time="19:00", activity="夜景或本地生活体验", location="住宿片区", tips="保留体力，不强行打卡"),
            ]
            title = spot
        plans.append(DayPlan(
            day=index + 1,
            title=title,
            area=spot,
            schedule=schedule,
            meals=[f"早餐尝试{request.destination}本地常见早点", "正餐选一道地方代表菜并提前说明忌口"],
            accommodation="选择轨道交通站步行10分钟内、夜间返程照明良好的住宿",
            daily_cost=f"约{daily_low}-{daily_high}元/人（餐饮、门票和市内交通）",
        ))
    return plans


def _build_budget(request: TripRequest) -> BudgetSummary:
    levels = {
        "经济": {"room": (220, 360), "food": (90, 150), "tickets": (60, 140), "local": (25, 60)},
        "舒适": {"room": (420, 680), "food": (160, 260), "tickets": (100, 220), "local": (50, 120)},
        "品质": {"room": (850, 1400), "food": (300, 520), "tickets": (160, 360), "local": (120, 260)},
    }[request.budget_level]
    rooms = max(1, math.ceil(request.travelers / 2))
    nights = max(1, request.days - 1)
    accommodation = tuple(value * rooms * nights for value in levels["room"])
    food = tuple(value * request.travelers * request.days for value in levels["food"])
    tickets = tuple(value * request.travelers * request.days for value in levels["tickets"])
    local = tuple(value * request.travelers * request.days for value in levels["local"])
    subtotal = (accommodation[0] + food[0] + tickets[0] + local[0], accommodation[1] + food[1] + tickets[1] + local[1])
    total = (round(subtotal[0] * 1.1), round(subtotal[1] * 1.1))
    return BudgetSummary(
        transport="按你的要求不列往返大交通价格；走法见行程总览",
        accommodation=f"{rooms}间房 × {nights}晚：约{accommodation[0]}-{accommodation[1]}元",
        food=f"{request.travelers}人 × {request.days}天：约{food[0]}-{food[1]}元",
        tickets=f"约{tickets[0]}-{tickets[1]}元（按每天1-2个收费项目估算）",
        local_transit=f"约{local[0]}-{local[1]}元（公交地铁为主，含少量打车）",
        total=f"约{total[0]}-{total[1]}元 / {request.travelers}人",
        note="总额含10%机动资金，不含往返大交通；住宿按每间2人估算，单人出行按1间房计算。",
    )


def _build_preparation(request: TripRequest) -> TravelPreparation:
    special = [f"下载{request.destination}离线地图，并保存住宿地址和返程枢纽名称"]
    if request.destination in {"拉萨", "西宁", "丽江", "大理", "香格里拉"}:
        special += ["防晒霜、墨镜、遮阳帽和润唇膏", "抵达高海拔地区首日降低运动强度，慢性病患者提前咨询医生"]
    if request.destination in {"三亚", "海口", "厦门", "青岛", "大连"}:
        special += ["防晒衣、速干衣和可密封湿衣袋", "涉水鞋或防滑凉鞋；下海前查看风浪和开放标识"]
    if request.destination in {"成都", "重庆", "长沙", "广州", "桂林", "杭州"}:
        special.append("折叠伞、轻薄雨衣和可防潮的证件袋")
    return TravelPreparation(
        essentials=["居民身份证或本次行程所需有效证件", "手机、支付工具和少量备用现金", "本人常用药与紧急联系人信息"],
        documents=["车票或航班信息离线截图", "酒店确认单与完整地址", "实名景区预约二维码及同行人证件"],
        clothing=[f"按{request.days}天准备可混搭上衣，并多带1套贴身衣物", "一双已磨合的防滑步行鞋", "轻便外套与可折叠备用袋"],
        health=["创可贴、消毒湿巾和肠胃药", "处方药保留原包装和用药说明", "防晒、防蚊用品按季节携带"],
        electronics=["手机充电器与充电线", "符合承运规则且标识清晰的充电宝", "耳机；摄影需求另带备用存储卡"],
        bookings=["住宿、往返交通和重点景区预约", "把每日首个景点地址加入地图收藏", "确认酒店入住时间、行李寄存和停车条件"],
        destination_specific=special,
        last_check=["出发前48小时复查天气与景区通知", "出发前24小时给手机和充电宝充满电", "核对证件、预约、行李重量和住宿地址"],
    )
