#!/bin/bash

# Master script to run all benchmark chunks in parallel

cd /Users/nikhilkhandekar/Documents/MedCalc-Web

echo "================================================"
echo "  Medical Calculator Benchmark Suite"
echo "  Using Browser-Use for Automated Testing"
echo "================================================"
echo ""

# Step 1: Sample 3 items per calculator
echo "📊 Sampling 3 test cases per calculator..."
python sample_by_calculator.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to sample test data"
    exit 1
fi

echo ""

# Step 2: Split the sampled data into chunks for parallel processing
echo "📊 Splitting sampled data into chunks..."
python split_test_data.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to split test data"
    exit 1
fi

echo ""

# Step 2: Run parallel benchmarks
echo "🚀 Running parallel benchmarks..."
python run_parallel_benchmarks.py

if [ $? -ne 0 ]; then
    echo "❌ Benchmarks encountered errors"
    exit 1
fi

echo ""

# Step 3: Aggregate results
echo "📊 Aggregating results from all chunks..."
python aggregate_results.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to aggregate results"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ Complete benchmark suite finished!"
echo "================================================"

