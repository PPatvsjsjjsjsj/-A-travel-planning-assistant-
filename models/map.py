from pydantic import BaseModel, Field


class MapRouteRequest(BaseModel):
    origin: str = Field(min_length=1, max_length=40)
    destination: str = Field(min_length=1, max_length=40)
    transport: str = Field(default="综合推荐", max_length=20)


class MapPoint(BaseModel):
    name: str
    longitude: float
    latitude: float
    kind: str


class MapRouteResponse(BaseModel):
    origin: str
    destination: str
    transport: str
    distance_km: int
    duration: str
    description: str
    points: list[MapPoint]
    disclaimer: str = "自驾由高德绘制实际道路；高铁、火车和飞机仅展示城市枢纽走向，不代表实时轨道或航路。"
