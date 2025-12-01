"""
Run benchmarks in parallel for all chunks
"""
import asyncio
import subprocess
import glob
import os
from pathlib import Path

async def run_chunk_benchmark(chunk_file: str, chunk_id: int):
    """Run benchmark for a single chunk"""
    log_file = f"benchmark_chunk_{chunk_id}.log"
    
    print(f"  ✓ Starting chunk {chunk_id}...")
    
    cmd = [
        "python", "benchmark_calculators.py",
        "--input", chunk_file,
        "--chunk-id", str(chunk_id)
    ]
    
    with open(log_file, 'w') as log:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd()
        )
        
        exit_code = await process.wait()
    
    if exit_code == 0:
        print(f"  ✅ Chunk {chunk_id} completed successfully")
    else:
        print(f"  ❌ Chunk {chunk_id} failed (exit code: {exit_code})")
    
    return exit_code

async def main():
    """Run all chunks in parallel"""
    # Find all chunk files
    chunk_files = sorted(glob.glob("test_data_chunk_*.csv"))
    
    if not chunk_files:
        print("❌ No chunk files found! Run split_test_data.py first.")
        return
    
    print("="*70)
    print(f"  Medical Calculator Benchmark Suite")
    print(f"  Running {len(chunk_files)} chunks in parallel")
    print("="*70)
    print()
    
    # Determine concurrency level (run 2 at a time to avoid overwhelming the system)
    max_concurrent = 2
    
    # Run chunks in batches
    all_tasks = []
    for i, chunk_file in enumerate(chunk_files, 1):
        task = run_chunk_benchmark(chunk_file, i)
        all_tasks.append(task)
    
    # Run with limited concurrency
    print(f"🚀 Launching benchmarks (max {max_concurrent} concurrent to avoid browser timeouts)...\n")
    
    # Process in batches
    results = []
    for i in range(0, len(all_tasks), max_concurrent):
        batch = all_tasks[i:i + max_concurrent]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        results.extend(batch_results)
        
        # Progress update
        completed = min(i + max_concurrent, len(all_tasks))
        print(f"\n📊 Progress: {completed}/{len(all_tasks)} chunks processed\n")
    
    # Summary
    print("\n" + "="*70)
    print("  All benchmarks complete!")
    print("="*70)
    print()
    
    successful = sum(1 for r in results if isinstance(r, int) and r == 0)
    failed = len(results) - successful
    
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    print()
    print("📁 Results files: benchmark_results_chunk_*.json")
    print("📊 Log files: benchmark_chunk_*.log")
    print()
    print("Run 'python aggregate_results.py' to combine all results.")
    print()

if __name__ == "__main__":
    asyncio.run(main())

