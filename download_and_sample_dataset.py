"""
Download MedCalc-Bench-Verified dataset from Hugging Face
and sample 5 instances per calculator
"""
import csv
import random
from collections import defaultdict
from datasets import load_dataset

def download_and_sample(samples_per_calculator: int = 5, output_file: str = "test_data_sampled_5_per_calc.csv"):
    """
    Download MedCalc-Bench-Verified dataset from Hugging Face
    and sample n instances per calculator
    
    Args:
        samples_per_calculator: Number of samples to take per calculator
        output_file: Output CSV file path
    """
    print("="*70)
    print("  Downloading MedCalc-Bench-Verified Dataset")
    print("  From: https://huggingface.co/datasets/nsk7153/MedCalc-Bench-Verified")
    print("="*70)
    print()
    
    # Load the dataset from Hugging Face
    print("📥 Downloading dataset from Hugging Face...")
    try:
        # Load both train and test splits
        dataset = load_dataset("nsk7153/MedCalc-Bench-Verified")
        print(f"  ✅ Dataset loaded successfully")
        print(f"  - Train split: {len(dataset['train'])} rows")
        print(f"  - Test split: {len(dataset['test'])} rows")
        print()
        
        # Combine train and test splits for sampling
        all_data = []
        for split_name, split_data in dataset.items():
            print(f"  Processing {split_name} split...")
            for row in split_data:
                all_data.append(row)
        
        print(f"  Total rows: {len(all_data)}")
        print()
        
    except Exception as e:
        print(f"  ❌ Error downloading dataset: {e}")
        return None
    
    # Group by calculator ID
    print("📊 Grouping data by calculator...")
    by_calculator = defaultdict(list)
    for row in all_data:
        calc_id = str(row.get('Calculator ID', ''))
        by_calculator[calc_id].append(row)
    
    print(f"  Found {len(by_calculator)} unique calculators")
    print()
    
    # Sample from each calculator
    print(f"🎲 Sampling {samples_per_calculator} instances per calculator...")
    sampled_rows = []
    for calc_id in sorted(by_calculator.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        calc_rows = by_calculator[calc_id]
        calc_name = calc_rows[0].get('Calculator Name', 'Unknown') if calc_rows else 'Unknown'
        
        # Randomly sample if we have more than needed
        if len(calc_rows) > samples_per_calculator:
            samples = random.sample(calc_rows, samples_per_calculator)
        else:
            samples = calc_rows
        
        sampled_rows.extend(samples)
        print(f"  Calculator {calc_id:>3} ({calc_name[:50]:<50}): {len(samples)}/{len(calc_rows)} samples")
    
    print()
    
    # Convert to CSV format
    print(f"💾 Writing sampled data to {output_file}...")
    if sampled_rows:
        # Get all field names from the first row
        fieldnames = list(sampled_rows[0].keys())
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sampled_rows)
        
        print(f"  ✅ Created {output_file} with {len(sampled_rows)} total rows")
        print(f"     ({len(by_calculator)} calculators × up to {samples_per_calculator} samples)")
    else:
        print("  ❌ No data to write")
        return None
    
    print()
    print("="*70)
    print("✅ Dataset download and sampling complete!")
    print("="*70)
    
    return output_file

if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)
    
    # Download and sample 5 instances per calculator
    download_and_sample(samples_per_calculator=5, output_file="test_data_sampled_5_per_calc.csv")

