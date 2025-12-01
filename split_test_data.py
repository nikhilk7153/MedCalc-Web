"""
Split test_data_sampled.csv into chunks for parallel processing
"""
import csv
from pathlib import Path

def split_csv_into_chunks(input_file: str, rows_per_chunk: int = 3):
    """Split CSV file into chunks of specified size"""
    
    # Read all rows
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    
    total_rows = len(rows)
    num_chunks = (total_rows + rows_per_chunk - 1) // rows_per_chunk  # Ceiling division
    
    print(f"Total data rows: {total_rows}")
    print(f"Rows per chunk: {rows_per_chunk}")
    print(f"Total chunks: {num_chunks}\n")
    
    # Create chunks
    chunk_num = 1
    for i in range(0, total_rows, rows_per_chunk):
        chunk_rows = rows[i:i + rows_per_chunk]
        output_file = f"test_data_chunk_{chunk_num}.csv"
        
        # Write chunk with header
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(chunk_rows)
        
        print(f"Created {output_file} with {len(chunk_rows)} rows")
        chunk_num += 1
    
    return num_chunks

if __name__ == "__main__":
    # Use the sampled file with 3 items per calculator
    num_chunks = split_csv_into_chunks("test_data_sampled_3_per_calc.csv", rows_per_chunk=33)
    print(f"\n✅ CSV splitting complete! Created {num_chunks} chunks.")

