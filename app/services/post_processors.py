from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from calculator_implementations.age_conversion import age_conversion

POST_PROCESSORS = {}


def _extract_value(field: Any) -> Optional[float]:
    if isinstance(field, (list, tuple)) and field:
        try:
            return float(field[0])
        except (TypeError, ValueError):
            return None
    try:
        return float(field)
    except (TypeError, ValueError):
        return None


def _extract_unit(field: Any) -> str:
    if isinstance(field, (list, tuple)) and len(field) > 1:
        return str(field[1]).lower()
    return ""


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def _convert_temperature_to_celsius(field: Any) -> Optional[float]:
    value = _extract_value(field)
    if value is None:
        return None
    unit = _extract_unit(field)
    if "c" in unit:
        return value
    if "f" in unit:
        return (value - 32.0) * (5.0 / 9.0)
    return value


def _derive_psi_risk_class(score: Optional[int], is_class_i: bool) -> Dict[str, str]:
    if is_class_i:
        return {
            "risk_class": "Risk Class I",
            "recommendation": "Very low risk. Outpatient care appropriate.",
        }

    if score is None:
        return {
            "risk_class": "Unknown",
            "recommendation": "Score unavailable. Please verify the inputs.",
        }

    if score <= 70:
        return {
            "risk_class": "Risk Class II",
            "recommendation": "Low risk. Outpatient care appropriate.",
        }
    if score <= 90:
        return {
            "risk_class": "Risk Class III",
            "recommendation": "Low risk. Consider outpatient management or brief observation.",
        }
    if score <= 130:
        return {
            "risk_class": "Risk Class IV",
            "recommendation": "Moderate risk. Recommend inpatient admission.",
        }

    return {
        "risk_class": "Risk Class V",
        "recommendation": "High risk. Recommend inpatient admission (consider ICU).",
    }


def _psi_processor(
    inputs: Dict[str, Any], raw_result: Dict[str, Any]
) -> Dict[str, Any]:
    score_value: Optional[int]
    try:
        score_value = int(round(float(raw_result.get("Answer"))))
    except (TypeError, ValueError):
        score_value = None

    age_years = None
    if "age" in inputs:
        try:
            age_years = age_conversion(inputs["age"])
        except Exception:  # pragma: no cover - defensive
            age_years = None

    heart_rate = _extract_value(inputs.get("heart_rate"))
    respiratory_rate = _extract_value(inputs.get("respiratory_rate"))
    systolic_bp = _extract_value(inputs.get("sys_bp"))
    temp_celsius = _convert_temperature_to_celsius(inputs.get("temperature"))

    comorbidities = [
        inputs.get("neoplastic_disease"),
        inputs.get("liver_disease"),
        inputs.get("chf"),
        inputs.get("cerebrovascular_disease"),
        inputs.get("renal_disease"),
    ]
    exam_findings = [
        inputs.get("altered_mental_status"),
        respiratory_rate is not None and respiratory_rate >= 30,
        systolic_bp is not None and systolic_bp < 90,
        temp_celsius is not None and (temp_celsius < 35 or temp_celsius >= 40),
        heart_rate is not None and heart_rate >= 125,
    ]

    is_class_i = (
        age_years is not None
        and age_years <= 50
        and not _as_bool(inputs.get("nursing_home_resident"))
        and not any(_as_bool(flag) for flag in comorbidities)
        and not any(exam_findings)
    )

    classification = _derive_psi_risk_class(score_value, is_class_i)

    return {
        "score": None if is_class_i else score_value,
        "raw_score": score_value,
        "risk_class": classification["risk_class"],
        "recommendation": classification["recommendation"],
        "is_class_i": is_class_i,
    }


POST_PROCESSORS[
    "psi-score-pneumonia-severity-index-for-cap"
] = _psi_processor


def apply_post_processors(
    calculator, inputs: Dict[str, Any], raw_result: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    processor = POST_PROCESSORS.get(calculator.slug)
    if not processor:
        return None
    return processor(inputs, raw_result)

