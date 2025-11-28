from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.registry import CalculatorDefinition, get_registry
from app.services.calculator_runner import execute_calculator

router = APIRouter()


def _serialize_summary(calculator: CalculatorDefinition) -> Dict[str, Any]:
    return {
        "id": calculator.id,
        "slug": calculator.slug,
        "name": calculator.name,
        "type": calculator.calculator_type,
    }


def _serialize_detail(calculator: CalculatorDefinition) -> Dict[str, Any]:
    summary = _serialize_summary(calculator)
    summary.update(
        {
            "question": calculator.question,
            "fields": calculator.list_fields(),
        }
    )
    return summary


@router.get("/")
def list_calculators() -> Dict[str, Any]:
    registry = get_registry()
    calculators = [_serialize_summary(calc) for calc in registry.list()]
    return {"calculators": calculators}


@router.get("/{slug}")
def get_calculator(slug: str) -> Dict[str, Any]:
    registry = get_registry()
    try:
        calculator = registry.get_by_slug(slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _serialize_detail(calculator)


@router.post("/{slug}")
def run_calculator(slug: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(
            status_code=400,
            detail="Request body must be a JSON object with calculator inputs.",
        )

    registry = get_registry()
    try:
        calculator = registry.get_by_slug(slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        return execute_calculator(calculator, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=400, detail=f"Missing required field: {exc}"
        ) from exc
    except Exception as exc:  # pragma: no cover - surfaced to clients
        raise HTTPException(status_code=500, detail=f"Calculator failed: {exc}") from exc

