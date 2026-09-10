from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.settings import BASE_DIR, SKILLS_DIR, settings
from agents.travel_agent import TravelAgent
from messaging.session_store import SessionStore
from models.chat import ChatRequest, ChatResponse, SessionResponse
from models.map import MapRouteRequest, MapRouteResponse
from models.trip import NaturalTripRequest, PlanResponse, TripRequest
from services.map_routes import build_map_route
from services.request_parser import parse_natural_request
from services.travel_planner import create_trip_plan
from skills.loader import SkillLoader


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="面向中国境内旅行的 DeepSeek 智能行程规划 API",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
skill_loader = SkillLoader(SKILLS_DIR)
session_store = SessionStore()
travel_agent = TravelAgent(session_store, skill_loader)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "deepseek_enabled": settings.deepseek_enabled,
            "amap_enabled": settings.amap_enabled,
            "amap_config": {
                "key": settings.amap_js_key,
                "securityJsCode": settings.amap_security_js_code,
            },
        },
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "deepseek_configured": settings.deepseek_enabled,
        "model": settings.deepseek_model,
        "amap_configured": settings.amap_enabled,
        "amap_key_present": bool(settings.amap_js_key.strip()),
        "amap_security_code_present": bool(settings.amap_security_js_code.strip()),
        "env_file": str(BASE_DIR / ".env"),
        "skills": len(skill_loader.skills),
    }


@app.get("/api/skills")
async def list_skills():
    return {"skills": skill_loader.list_skills()}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(payload: ChatRequest):
    return await travel_agent.chat(payload.message, payload.session_id)


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return SessionResponse(
        session_id=session.session_id,
        messages=session.messages,
        request=session.trip_request,
        plan=session.plan,
        skills_used=session.skills_used,
    )


@app.delete("/api/sessions/{session_id}")
async def clear_session(session_id: str):
    return {"deleted": session_store.delete(session_id)}


@app.post("/api/map/route", response_model=MapRouteResponse)
async def map_route(payload: MapRouteRequest):
    return build_map_route(payload.origin, payload.destination, payload.transport)


@app.post("/api/plan", response_model=PlanResponse)
async def plan_trip(payload: TripRequest):
    skill_names, skill_context = skill_loader.build_context(payload)
    plan = await create_trip_plan(payload, skill_context)
    return PlanResponse(request=payload, plan=plan, skills_used=skill_names)


@app.post("/api/plan/natural", response_model=PlanResponse)
async def plan_trip_from_text(payload: NaturalTripRequest):
    request = parse_natural_request(payload.message)
    skill_names, skill_context = skill_loader.build_context(request)
    plan = await create_trip_plan(request, skill_context)
    return PlanResponse(request=request, plan=plan, skills_used=skill_names)
