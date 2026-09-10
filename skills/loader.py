import re
from dataclasses import dataclass
from pathlib import Path

from models.trip import TripRequest


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str


class SkillLoader:
    def __init__(self, root: Path):
        self.root = root
        self.skills = self._load_all()

    def _load_all(self) -> dict[str, Skill]:
        skills = {}
        for path in sorted(self.root.glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
            if not match:
                continue
            metadata, body = match.groups()
            name = self._field(metadata, "name") or path.parent.name
            description = self._field(metadata, "description")
            skills[name] = Skill(name=name, description=description, body=body.strip())
        return skills

    @staticmethod
    def _field(metadata: str, name: str) -> str:
        match = re.search(rf"^{name}:\s*(.+)$", metadata, re.MULTILINE)
        return match.group(1).strip().strip('"') if match else ""

    def list_skills(self) -> list[dict[str, str]]:
        return [{"name": item.name, "description": item.description} for item in self.skills.values()]

    def select(self, request: TripRequest) -> list[Skill]:
        selected = {
            "weather-advice",
            "route-planning",
            "trip-budget",
            "local-food",
            "regional-culture",
            "travel-pitfalls",
            "travel-preparation",
        }
        text = " ".join([request.notes, request.transport_preference, *request.interests])
        if any(word in text for word in ("沿途", "经停", "中转", "环线", "自驾")):
            selected.add("enroute-attractions")
        if any(word in text for word in ("过敏", "忌口", "不吃", "素食", "清真", "糖尿病", "痛风")):
            selected.add("dietary-taboos")
        if any(word in text for word in ("民族", "村寨", "乡村", "寺", "教堂", "清真寺")):
            selected.add("local-customs")
        if any(word in text for word in ("节日", "节庆", "庙会", "仪式", "庆典")):
            selected.add("festival-etiquette")
        return [self.skills[name] for name in sorted(selected) if name in self.skills]

    def build_context(self, request: TripRequest) -> tuple[list[str], str]:
        selected = self.select(request)
        names = [skill.name for skill in selected]
        context = "\n\n".join(f"<skill name=\"{skill.name}\">\n{skill.body}\n</skill>" for skill in selected)
        return names, context
