"""Shared parsing and scoring helpers for benchmark runners."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

JSON_ANSWER_PATTERN = re.compile(r'\{[^}]*"answer"[^}]*\}')
NUMBER_PATTERN = re.compile(r'-?\d+(?:\.\d+)?')
DATE_TOKEN_PATTERN = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
DATE_FORMATS = (
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%Y-%m-%d",
)


def parse_agent_result(result: Any) -> dict[str, Any]:
    """Extract a usable answer payload from agent output."""
    result_str = str(result).strip()
    final_json = None
    agent_answer: Any = None
    extraction_method = "unknown"

    try:
        json_match = JSON_ANSWER_PATTERN.search(result_str)
        if json_match:
            final_json = json.loads(json_match.group())
            agent_answer = final_json.get("answer")
            extraction_method = "json_embedded"
        else:
            final_json = json.loads(result_str)
            agent_answer = final_json.get("answer")
            extraction_method = "json_full"
    except (json.JSONDecodeError, AttributeError, TypeError):
        # Fallback keeps behavior compatible with existing runners while tagging
        # the extraction method so scoring can flag likely mis-extractions later.
        numbers = NUMBER_PATTERN.findall(result_str)
        if numbers:
            agent_answer = float(numbers[0])
            extraction_method = "first_number"
        else:
            agent_answer = result_str
            extraction_method = "text_fallback"

    return {
        "raw_response": result_str,
        "agent_json": final_json,
        "agent_answer": agent_answer,
        "extraction_method": extraction_method,
    }


def evaluate_prediction(
    *,
    agent_answer: Any,
    ground_truth: str,
    output_type: str,
    lower_limit: str | None,
    upper_limit: str | None,
    raw_response: str,
    extraction_method: str,
) -> dict[str, Any]:
    """Score an agent answer using output-type-aware rules."""
    output_type_norm = (output_type or "").strip().lower()

    if output_type_norm == "date":
        # Date tasks are evaluated as exact matches after normalization to avoid
        # false negatives from format-only differences (MM/DD/YYYY vs ISO).
        truth_date = _parse_date(ground_truth)
        pred_date = _parse_date(agent_answer)

        if truth_date is None:
            return {
                "is_correct": False,
                "failure_type": "ground_truth_parse_error",
                "scoring_rule": "exact_date",
                "normalized_truth": str(ground_truth),
                "normalized_prediction": str(agent_answer),
                "lower_bound": None,
                "upper_bound": None,
            }

        if pred_date is None:
            failure_type = "answer_parse_error"
            if extraction_method == "first_number" and _contains_correct_date(raw_response, truth_date):
                failure_type = "wrong_number_extracted"
            return {
                "is_correct": False,
                "failure_type": failure_type,
                "scoring_rule": "exact_date",
                "normalized_truth": truth_date.isoformat(),
                "normalized_prediction": str(agent_answer),
                "lower_bound": None,
                "upper_bound": None,
            }

        is_correct = pred_date == truth_date
        return {
            "is_correct": is_correct,
            "failure_type": None if is_correct else "date_mismatch",
            "scoring_rule": "exact_date",
            "normalized_truth": truth_date.isoformat(),
            "normalized_prediction": pred_date.isoformat(),
            "lower_bound": None,
            "upper_bound": None,
        }

    truth_num = _coerce_float(ground_truth)
    if truth_num is None:
        pred_text = str(agent_answer).strip()
        truth_text = str(ground_truth).strip()
        is_correct = pred_text == truth_text
        return {
            "is_correct": is_correct,
            "failure_type": None if is_correct else "answer_parse_error",
            "scoring_rule": "exact_match_string",
            "normalized_truth": truth_text,
            "normalized_prediction": pred_text,
            "lower_bound": None,
            "upper_bound": None,
        }

    pred_num = _coerce_float(agent_answer)
    lower_bound, upper_bound, scoring_rule = _numeric_bounds(
        truth_num=truth_num,
        output_type=output_type_norm,
        lower_limit=lower_limit,
        upper_limit=upper_limit,
    )

    if pred_num is None:
        failure_type = "answer_parse_error"
        if extraction_method == "first_number" and _contains_correct_numeric(
            raw_response,
            lower_bound,
            upper_bound,
            output_type_norm,
        ):
            failure_type = "wrong_number_extracted"

        return {
            "is_correct": False,
            "failure_type": failure_type,
            "scoring_rule": scoring_rule,
            "normalized_truth": truth_num,
            "normalized_prediction": agent_answer,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        }

    if output_type_norm == "integer":
        normalized_pred = int(round(pred_num))
        is_correct = lower_bound <= normalized_pred <= upper_bound
    else:
        normalized_pred = pred_num
        is_correct = lower_bound <= normalized_pred <= upper_bound

    failure_type = None if is_correct else "numeric_incorrect"
    if (not is_correct) and extraction_method == "first_number":
        if _contains_correct_numeric(raw_response, lower_bound, upper_bound, output_type_norm):
            failure_type = "wrong_number_extracted"

    normalized_truth: Any
    if output_type_norm == "integer":
        normalized_truth = int(round(truth_num))
    else:
        normalized_truth = truth_num

    return {
        "is_correct": is_correct,
        "failure_type": failure_type,
        "scoring_rule": scoring_rule,
        "normalized_truth": normalized_truth,
        "normalized_prediction": normalized_pred,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    }


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    for token in DATE_TOKEN_PATTERN.findall(text):
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(token, fmt).date()
            except ValueError:
                continue

    return None


def _contains_correct_date(text: str, truth_date: date) -> bool:
    for token in DATE_TOKEN_PATTERN.findall(text):
        parsed = _parse_date(token)
        if parsed == truth_date:
            return True
    return False


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", "")
    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def _numeric_bounds(
    *,
    truth_num: float,
    output_type: str,
    lower_limit: str | None,
    upper_limit: str | None,
) -> tuple[float, float, str]:
    lower = _coerce_float(lower_limit)
    upper = _coerce_float(upper_limit)
    if lower is not None and upper is not None:
        # Normalize bound ordering because some datasets include negative values.
        return (min(lower, upper), max(lower, upper), "range_limit")

    if output_type == "integer":
        rounded_truth = float(round(truth_num))
        return (rounded_truth, rounded_truth, "exact_integer")

    tolerance = 0.05 * abs(truth_num)
    return (truth_num - tolerance, truth_num + tolerance, "percent_tolerance")


def _contains_correct_numeric(text: str, lower_bound: float, upper_bound: float, output_type: str) -> bool:
    # Used to distinguish "agent produced usable value but harness grabbed the
    # wrong token" from genuine incorrect predictions.
    for token in NUMBER_PATTERN.findall(text):
        try:
            value = float(token)
        except ValueError:
            continue

        if output_type == "integer":
            value = float(round(value))

        if lower_bound <= value <= upper_bound:
            return True

    return False
