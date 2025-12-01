"""
Sample 3 test cases per calculator from test_data_sampled.csv
"""
import csv
from collections import defaultdict
from pathlib import Path

def sample_by_calculator(input_file: str, samples_per_calculator: int = 3):
    """Sample n rows per calculator ID"""
    
    # Read all rows
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Group by calculator ID
    by_calculator = defaultdict(list)
    for row in rows:
        calc_id = row['Calculator ID']
        by_calculator[calc_id].append(row)
    
    print(f"Total rows in original file: {len(rows)}")
    print(f"Unique calculators: {len(by_calculator)}")
    print(f"Samples per calculator: {samples_per_calculator}\n")
    
    # Sample from each calculator
    sampled_rows = []
    for calc_id, calc_rows in sorted(by_calculator.items(), key=lambda x: int(x[0])):
        calc_name = calc_rows[0]['Calculator Name'] if calc_rows else 'Unknown'
        samples = calc_rows[:samples_per_calculator]
        sampled_rows.extend(samples)
        print(f"Calculator {calc_id} ({calc_name}): {len(samples)} samples")
    
    # Write sampled data
    output_file = f"test_data_sampled_{samples_per_calculator}_per_calc.csv"
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        if sampled_rows:
            writer = csv.DictWriter(f, fieldnames=sampled_rows[0].keys())
            writer.writeheader()
            writer.writerows(sampled_rows)
    
    print(f"\n✅ Created {output_file} with {len(sampled_rows)} total rows")
    print(f"   ({len(by_calculator)} calculators × {samples_per_calculator} samples)")
    
    return output_file

if __name__ == "__main__":
    sample_by_calculator("test_data_sampled.csv", samples_per_calculator=3)

