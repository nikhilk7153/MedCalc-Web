#!/bin/bash

# Run benchmarks sequentially (one chunk at a time) to avoid browser timeouts

cd /Users/nikhilkhandekar/Documents/MedCalc-Web

echo "================================================"
echo "  Sequential Benchmark Runner"
echo "  Running chunks one at a time"
echo "================================================"
echo ""

# Check for chunk files
CHUNKS=$(ls test_data_chunk_*.csv 2>/dev/null | wc -l)

if [ "$CHUNKS" -eq 0 ]; then
    echo "❌ No chunk files found. Run sample and split first:"
    echo "   python sample_by_calculator.py"
    echo "   python split_test_data.py"
    exit 1
fi

echo "📊 Found $CHUNKS chunk files"
echo ""

# Clean up old results
rm -f benchmark_results_chunk_*.json
rm -f benchmark_chunk_*.log

# Run each chunk sequentially
for i in $(seq 1 $CHUNKS); do
    echo "🚀 Running chunk $i/$CHUNKS..."
    python benchmark_calculators.py \
        --input test_data_chunk_$i.csv \
        --chunk-id $i \
        > benchmark_chunk_$i.log 2>&1
    
    if [ $? -eq 0 ]; then
        echo "  ✅ Chunk $i completed"
    else
        echo "  ❌ Chunk $i failed (check benchmark_chunk_$i.log)"
    fi
    
    # Small delay between chunks
    sleep 2
done

echo ""
echo "📊 Aggregating results..."
python aggregate_results.py

echo ""
echo "✅ Sequential benchmark complete!"

