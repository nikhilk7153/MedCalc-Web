from __future__ import annotations

import importlib
from typing import Any, Dict, Tuple

from app.registry import CalculatorDefinition
from app.services.post_processors import apply_post_processors

_callable_cache: Dict[Tuple[str, str], Any] = {}


def _get_callable(calculator: CalculatorDefinition):
    cache_key = (calculator.module_path, calculator.function_name)
    if cache_key in _callable_cache:
        return _callable_cache[cache_key]

    module = importlib.import_module(calculator.module_path)
    function = getattr(module, calculator.function_name)
    _callable_cache[cache_key] = function
    return function


def execute_calculator(
    calculator: CalculatorDefinition, payload: Dict[str, Any]
) -> Dict[str, Any]:
    python_payload = calculator.translate_inputs(payload)
    calculator_callable = _get_callable(calculator)
    raw_result = calculator_callable(python_payload)

    if not isinstance(raw_result, dict):
        raise ValueError(
            f"Calculator '{calculator.slug}' returned an unexpected result. "
            "Expected a dictionary containing 'Answer' and 'Explanation'."
        )

    response: Dict[str, Any] = {
        "calculator_id": calculator.id,
        "calculator_slug": calculator.slug,
        "calculator_name": calculator.name,
        "answer": raw_result.get("Answer"),
        "explanation": raw_result.get("Explanation"),
        "raw_response": raw_result,
    }

    response.update(
        apply_post_processors(calculator, python_payload, raw_result) or {}
    )

    return response

