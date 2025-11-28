from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.settings import CALC_PATH_FILE, NAME_TO_PYTHON_FILE

META_KEYS = {
    "file path",
    "explanation function",
    "calculator name",
    "type",
    "question",
}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "calculator"


@dataclass(frozen=True)
class CalculatorDefinition:
    id: str
    name: str
    slug: str
    module_path: str
    function_name: str
    calculator_type: Optional[str] = None
    question: Optional[str] = None
    field_map: Dict[str, str] = field(default_factory=dict)

    def list_fields(self) -> List[Dict[str, str]]:
        return [
            {"label": label, "python_name": python_name}
            for label, python_name in self.field_map.items()
        ]

    def translate_inputs(self, raw_inputs: Dict[str, Any]) -> Dict[str, Any]:
        translated: Dict[str, Any] = {}
        for label, python_name in self.field_map.items():
            if label in raw_inputs:
                translated[python_name] = raw_inputs[label]

        for key, value in raw_inputs.items():
            if key not in self.field_map and key not in translated:
                translated[key] = value

        return translated


class CalculatorRegistry:
    def __init__(self, calculators: Iterable[CalculatorDefinition]) -> None:
        calculators_list = list(calculators)
        self._calculators = calculators_list
        self._by_slug = {calculator.slug: calculator for calculator in calculators_list}
        self._by_id = {calculator.id: calculator for calculator in calculators_list}

    def list(self) -> List[CalculatorDefinition]:
        return list(self._calculators)

    def get_by_slug(self, slug: str) -> CalculatorDefinition:
        try:
            return self._by_slug[slug]
        except KeyError as exc:
            raise KeyError(f"Unknown calculator slug '{slug}'") from exc


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def _build_definitions() -> List[CalculatorDefinition]:
    calc_path = _load_json(CALC_PATH_FILE)
    name_map = _load_json(NAME_TO_PYTHON_FILE)

    path_by_id = {
        str(entry["Calculator ID"]): {
            "name": calculator_name,
            "file_path": entry["File Path"],
        }
        for calculator_name, entry in calc_path.items()
        if "Calculator ID" in entry
    }

    slug_counts: Dict[str, int] = {}
    calculators: List[CalculatorDefinition] = []

    for calculator_id, entry in name_map.items():
        normalized_meta_keys = {key.lower() for key in entry.keys()}
        metadata: Dict[str, Any] = {
            key.lower(): value for key, value in entry.items() if key.lower() in META_KEYS
        }
        field_map = {
            key: value for key, value in entry.items() if key.lower() not in META_KEYS
        }

        module_rel_path = (
            path_by_id.get(calculator_id, {}).get("file_path")
            or metadata.get("file path")
        )
        function_name = metadata.get("explanation function")
        calculator_name = metadata.get("calculator name") or path_by_id.get(
            calculator_id, {}
        ).get("name")

        if not module_rel_path or not function_name or not calculator_name:
            continue

        module_path = (
            Path(module_rel_path).with_suffix("").as_posix().replace("/", ".")
        )

        slug = _slugify(calculator_name)
        slug_counts[slug] = slug_counts.get(slug, 0) + 1
        if slug_counts[slug] > 1:
            slug = f"{slug}-{slug_counts[slug]}"

        calculators.append(
            CalculatorDefinition(
                id=str(calculator_id),
                name=calculator_name,
                slug=slug,
                module_path=module_path,
                function_name=function_name,
                calculator_type=metadata.get("type"),
                question=metadata.get("question"),
                field_map=field_map,
            )
        )

    return calculators


@lru_cache(maxsize=1)
def get_registry() -> CalculatorRegistry:
    return CalculatorRegistry(_build_definitions())

