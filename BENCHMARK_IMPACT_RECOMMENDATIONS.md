# Benchmark Impact Recommendations

This document proposes practical improvements to increase the value and interpretability of the MedCalc benchmark for model and agent evaluation.

## Goals

- Separate medical-calculation signal from web-automation noise.
- Improve reproducibility across time and calculator sites.
- Make failures actionable for model and harness improvements.

## Immediate Fixes (High Priority)

1. Output-type aware scoring
- Dispatch scoring by `Output Type` (`decimal`, `integer`, `date`) instead of treating every answer as float.
- Respect `Lower Limit` / `Upper Limit` when available.
- Normalize dates before comparison (e.g., parse and compare in ISO format).

2. Stage-separated metrics
- Report:
  - `coverage_rate` (not skipped)
  - `ui_success` (calculator result reached)
  - `parse_success`
  - `end_to_end_accuracy`
  - `conditional_accuracy` (correct among parseable answers)

3. Failure taxonomy
- Classify failures into explicit buckets such as:
  - `coverage_missing_target`
  - `input_extraction_error`
  - `ui_navigation_error`
  - `result_not_visible`
  - `answer_parse_error`
  - `wrong_number_extracted`
  - `numeric_incorrect`
  - `runtime_exception`

4. Row-level metadata passthrough
- Include in every result record:
  - `row_number`
  - `calculator_id`
  - `category`
  - `output_type`
  - `site` (`local`, `mdapp`, `omni`)

5. Per-case timing
- Add per-case `timing` object:
  - `wall_seconds`
  - `agent_steps`
  - `llm_calls` (if available)
  - `total_tokens` (if available)

## Reporting Improvements

1. Category-stratified and output-type-stratified summaries
- Publish metrics by `Category` and `Output Type` in addition to overall values.
- Avoid relying only on blended accuracy.

2. Reproducibility manifest
- Store benchmark metadata in outputs:
  - dataset version/hash
  - runner version
  - model id
  - prompt version
  - timestamp (UTC)

3. Site-specific leaderboards
- Report local and external-site results separately.
- Treat external-site runs as robustness tracks rather than canonical benchmark scores.

## Dataset Notes

- The benchmark data evolves across releases; outputs should record a dataset identifier/hash.
- If future clinical interpretation metrics are desired (e.g., risk-band agreement), dataset enrichment is needed (calculator-specific band mappings).

## Suggested Rollout

1. Add metadata and failure taxonomy.
2. Add staged metrics and stratified reporting.
3. Add reproducibility manifest fields.
4. Add phase-2 clinical interpretation metrics once mappings are curated.
