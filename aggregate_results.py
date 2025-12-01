"""
Aggregate benchmark results from multiple chunks into a single report
"""
import json
import glob
from pathlib import Path
from datetime import datetime

def aggregate_results():
    """Combine results from all chunk files"""
    
    # Find all chunk result files
    result_files = sorted(glob.glob("benchmark_results_chunk_*.json"))
    
    if not result_files:
        print("❌ No chunk result files found!")
        return
    
    print(f"📊 Found {len(result_files)} result files to aggregate\n")
    
    # Aggregate stats
    combined_stats = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "by_calculator": {}
    }
    
    all_results = []
    
    # Load and combine all results
    for file in result_files:
        print(f"  Reading {file}...")
        with open(file, 'r') as f:
            data = json.load(f)
            
        # Aggregate overall stats
        combined_stats["total"] += data["stats"]["total"]
        combined_stats["passed"] += data["stats"]["passed"]
        combined_stats["failed"] += data["stats"]["failed"]
        combined_stats["errors"] += data["stats"]["errors"]
        
        # Aggregate per-calculator stats
        for calc, stats in data["stats"]["by_calculator"].items():
            if calc not in combined_stats["by_calculator"]:
                combined_stats["by_calculator"][calc] = {
                    "total": 0, "passed": 0, "failed": 0, "errors": 0
                }
            
            calc_stats = combined_stats["by_calculator"][calc]
            calc_stats["total"] += stats["total"]
            calc_stats["passed"] += stats["passed"]
            calc_stats["failed"] += stats["failed"]
            calc_stats["errors"] += stats["errors"]
        
        # Collect all results
        all_results.extend(data["results"])
    
    # Save aggregated results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"benchmark_results_aggregated_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "stats": combined_stats,
            "results": all_results,
            "timestamp": timestamp,
            "num_chunks": len(result_files)
        }, f, indent=2)
    
    print(f"\n✅ Aggregated results saved to {output_file}\n")
    
    # Print summary
    print("="*70)
    print("📊 AGGREGATED BENCHMARK SUMMARY")
    print("="*70)
    
    total = combined_stats["total"]
    passed = combined_stats["passed"]
    failed = combined_stats["failed"]
    errors = combined_stats["errors"]
    
    print(f"\nOverall Results (from {len(result_files)} chunks):")
    print(f"  Total Tests:  {total}")
    if total > 0:
        print(f"  ✅ Passed:    {passed} ({passed/total*100:.1f}%)")
        print(f"  ❌ Failed:    {failed} ({failed/total*100:.1f}%)")
        print(f"  ⚠️ Errors:    {errors} ({errors/total*100:.1f}%)")
    
    print(f"\nBy Calculator:")
    for calc, stats in sorted(combined_stats["by_calculator"].items()):
        total_calc = stats["total"]
        passed_calc = stats["passed"]
        if total_calc > 0:
            print(f"  {calc}:")
            print(f"    ✅ {passed_calc}/{total_calc} passed ({passed_calc/total_calc*100:.1f}%)")
    
    print("\n" + "="*70)
    
    return output_file

if __name__ == "__main__":
    aggregate_results()

