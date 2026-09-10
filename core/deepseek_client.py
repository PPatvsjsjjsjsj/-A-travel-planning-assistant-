import asyncio
import json
import re
import urllib.error
import urllib.request

from config.settings import settings


class DeepSeekConfigurationError(RuntimeError):
    pass


async def create_chat_completion(messages: list[dict], **options) -> str:
    if not settings.deepseek_enabled:
        raise DeepSeekConfigurationError("未配置 DEEPSEEK_API_KEY")

    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": settings.deepseek_model,
        "messages": messages,
        **options,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
    )

    def send_request() -> dict:
        try:
            with urllib.request.urlopen(request, timeout=settings.deepseek_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"DeepSeek API 返回 HTTP {exc.code}: {detail}") from exc

    data = await asyncio.to_thread(send_request)
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("DeepSeek 返回结构异常") from exc


def extract_json_object(content: str) -> dict:
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("DeepSeek 未返回有效的 JSON 对象")
        return json.loads(cleaned[start : end + 1])
