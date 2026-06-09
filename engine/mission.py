from dataclasses import dataclass, field
from pathlib import Path
import yaml

from ui.lang import get_lang


def _localized(value) -> str:
    if isinstance(value, dict):
        lang = get_lang()
        return value.get(lang, value.get("en", str(value)))
    return str(value) if value else ""


def _localized_list(value) -> list[str]:
    if isinstance(value, dict):
        lang = get_lang()
        result = value.get(lang, value.get("en", []))
        return result if isinstance(result, list) else [str(result)]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


@dataclass
class Objective:
    id: str
    _description: object  # str or dict
    objective_type: str
    target: dict = field(default_factory=dict)
    completed: bool = False

    @property
    def description(self) -> str:
        return _localized(self._description)


@dataclass
class Mission:
    id: str
    _title: object
    _briefing: object
    network_id: str
    objectives: list[Objective] = field(default_factory=list)
    rewards: dict = field(default_factory=dict)
    prerequisites: list[str] = field(default_factory=list)
    _hints: object = field(default_factory=list)
    hint_index: int = 0

    @property
    def title(self) -> str:
        return _localized(self._title)

    @property
    def briefing(self) -> str:
        return _localized(self._briefing)

    @property
    def hints(self) -> list[str]:
        return _localized_list(self._hints)

    def is_complete(self) -> bool:
        return all(obj.completed for obj in self.objectives)

    def get_next_hint(self) -> str | None:
        hints = self.hints
        if self.hint_index < len(hints):
            hint = hints[self.hint_index]
            self.hint_index += 1
            return hint
        return None

    def check_objective(self, objective_type: str, **kwargs) -> Objective | None:
        for obj in self.objectives:
            if obj.completed:
                continue
            if obj.objective_type != objective_type:
                continue

            if objective_type == "discover_hosts":
                count = kwargs.get("count", 0)
                if count >= obj.target.get("count", 0):
                    obj.completed = True
                    return obj

            elif objective_type == "compromise_host":
                ip = kwargs.get("ip", "")
                if ip == obj.target.get("ip", ""):
                    obj.completed = True
                    return obj

            elif objective_type == "read_file":
                ip = kwargs.get("ip", "")
                filepath = kwargs.get("file", "")
                if ip == obj.target.get("ip", "") and filepath == obj.target.get("file", ""):
                    obj.completed = True
                    return obj

            elif objective_type == "download_file":
                ip = kwargs.get("ip", "")
                filepath = kwargs.get("file", "")
                if ip == obj.target.get("ip", "") and filepath == obj.target.get("file", ""):
                    obj.completed = True
                    return obj

        return None


def load_mission(yaml_path: str | Path) -> Mission:
    yaml_path = Path(yaml_path)
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    objectives = []
    for obj_data in data.get("objectives", []):
        objectives.append(Objective(
            id=obj_data["id"],
            _description=obj_data["description"],
            objective_type=obj_data["objective_type"],
            target=obj_data.get("target", {}),
        ))

    return Mission(
        id=data["id"],
        _title=data["title"],
        _briefing=data["briefing"],
        network_id=data["network_id"],
        objectives=objectives,
        rewards=data.get("rewards", {}),
        prerequisites=data.get("prerequisites", []),
        _hints=data.get("hints", []),
    )
