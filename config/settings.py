import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE_DIR / "skills"
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "探山"
    app_version: str = "1.0.0"
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_timeout: float = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
    max_plan_days: int = int(os.getenv("MAX_PLAN_DAYS", "15"))
    amap_js_key: str = os.getenv("AMAP_JS_KEY", "")
    amap_security_js_code: str = os.getenv("AMAP_SECURITY_JS_CODE", "")

    @property
    def deepseek_enabled(self) -> bool:
        return bool(self.deepseek_api_key.strip())

    @property
    def amap_enabled(self) -> bool:
        return bool(self.amap_js_key.strip() and self.amap_security_js_code.strip())


settings = Settings()
