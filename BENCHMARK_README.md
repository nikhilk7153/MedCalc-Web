# Medical Calculator Benchmark System

Automated testing suite for MedCalc-Web calculators using browser-use.

## Overview

This benchmark system tests calculator accuracy by:
- Sampling 3 test cases per calculator ID (55 calculators × 3 = 165 tests)
- Splitting into 5 chunks for parallel processing (33 tests per chunk)
- Running browser-use agents in parallel across chunks
- Comparing calculator outputs against ground truth
- Aggregating results into comprehensive reports

## Files Created

- **Sampled data**: `test_data_sampled_3_per_calc.csv` - 165 balanced test cases
- **5 chunk files**: `test_data_chunk_1.csv` through `test_data_chunk_5.csv`
- **Sampling script**: `sample_by_calculator.py` - Samples 3 per calculator
- **Benchmark script**: `benchmark_calculators.py` - Core testing logic
- **Splitting script**: `split_test_data.py` - Splits CSV into chunks
- **Parallel runner**: `run_parallel_benchmarks.py` - Runs chunks in parallel
- **Aggregator**: `aggregate_results.py` - Combines results
- **Master script**: `run_all_benchmarks.sh` - Runs everything

## Prerequisites

1. **Browser-Use API Key**: Set your `BROWSER_USE_API_KEY` environment variable
   ```bash
   export BROWSER_USE_API_KEY="your-key-here"
   ```
   Get a key at: https://cloud.browser-use.com/new-api-key

2. **Running Server**: Ensure FastAPI server is running
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## Quick Start

Run the complete benchmark suite:

```bash
./run_all_benchmarks.sh
```

This will:
1. Sample 3 test cases per calculator (165 total)
2. Split into 5 chunks (33 rows each)
3. Run benchmarks in parallel (5 concurrent chunks)
4. Aggregate all results into a final report

## Manual Usage

### 1. Sample Data (3 per calculator)
```bash
python sample_by_calculator.py
```

### 2. Split Into Chunks
```bash
python split_test_data.py
```

### 3. Run Parallel Benchmarks
```bash
python run_parallel_benchmarks.py
```

### 4. Aggregate Results
```bash
python aggregate_results.py
```

## Individual Chunk Testing

Test a single chunk:
```bash
python benchmark_calculators.py --input test_data_chunk_1.csv --chunk-id 1
```

## Output Files

- `benchmark_chunk_*.log` - Individual chunk logs
- `benchmark_results_chunk_*.json` - Individual chunk results
- `benchmark_results_aggregated_*.json` - Combined results from all chunks

## Concurrency

The system runs **5 chunks concurrently** to avoid overwhelming the system while maintaining good parallelism. This can be adjusted in `run_parallel_benchmarks.py` by changing the `max_concurrent` variable.

## Notes

- **Balanced Sampling**: 3 test cases per calculator ensures even coverage across all 55 calculators
- **Parallel Execution**: 5 chunks run concurrently for efficient testing
- **Independent Agents**: Each browser-use agent runs in its own browser instance
- **Results Tracking**: Includes pass/fail status, execution time, and detailed error information
- **Accuracy Checking**: Ground truth comparison uses 5% tolerance or specified upper/lower limits

