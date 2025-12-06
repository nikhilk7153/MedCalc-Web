"""
Simple sequential benchmark runner - continues from previous run
Uses only MDApp mappings from the provided CSV file
"""
import asyncio
import csv
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Create screenshots, trajectories, and logs directories
SCREENSHOT_DIR = Path("benchmark_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)
TRAJECTORY_DIR = Path("benchmark_trajectories")
TRAJECTORY_DIR.mkdir(exist_ok=True)
LOGS_DIR = Path("benchmark_logs")
LOGS_DIR.mkdir(exist_ok=True)

def load_mdapp_mappings(csv_path):
    """Load calculator name to URL mappings from the MDApp CSV file"""
    mappings = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                calc_id = row[0].strip()
                short_name = row[1].strip()
                url = row[2].strip() if row[2].strip() else None
                
                if url:
                    mappings[short_name.lower()] = url
    
    return mappings

# Map full calculator names to short names used in CSV
FULL_NAME_TO_SHORT = {
    "Creatinine Clearance (Cockcroft-Gault Equation)": "creatinine clearance",
    "CKD-EPI Equations for Glomerular Filtration Rate": "ckd-epi",
    "CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk": "cha2dvasc score",
    "Mean Arterial Pressure (MAP)": "mean arterial pressure",
    "Body Mass Index (BMI)": "bmi",
    "Calcium Correction for Hypoalbuminemia": "corrected calcium",
    "Wells' Criteria for Pulmonary Embolism": "wells pe",
    "MDRD GFR Equation": "mdrd gfr",
    "Ideal Body Weight": "bmi",  # Uses BMI calculator
    "QTc Bazett Calculator": "qtc bazzett",
    "Estimated Due Date": "edd",
    "Child-Pugh Score for Cirrhosis Mortality": "child pugh",
    "Wells' Criteria for DVT": "wells dvt",
    "Revised Cardiac Risk Index for Pre-Operative Risk": "revised cardiac risk index",
    "HEART Score for Major Cardiac Events": "heart score",
    "Fibrosis-4 (FIB-4) Index for Liver Fibrosis": "fib-4",
    "Centor Score (Modified/McIsaac) for Strep Pharyngitis": "centor socre",  # Note: typo in original CSV
    "Glasgow Coma Score (GCS)": None,  # Not in MDApp
    "Maintenance Fluids Calculations": "maintenance fluid",
    "MELD Na (UNOS/OPTN)": "meld na",
    "Steroid Conversion Calculator": "steroid conversion",
    "HAS-BLED Score for Major Bleeding Risk": "has-bled",
    "Sodium Correction for Hyperglycemia": "sodium correction",
    "Glasgow-Blatchford Bleeding Score (GBS)": "glasgow blatchford score",
    "APACHE II Score": "apache ii",
    "PSI Score: Pneumonia Severity Index for CAP": "psi",
    "Serum Osmolality": "serum osmolarity",
    "HOMA-IR (Homeostatic Model Assessment for Insulin Resistance)": "homa-ir",
    "Charlson Comorbidity Index (CCI)": "cci",
    "FeverPAIN Score for Strep Pharyngitis": "feverpain",
    "Caprini Score for Venous Thromboembolism (2005)": "caprini",
    "Free Water Deficit": "free water deficit",
    "Anion Gap": "anion gap",
    "Fractional Excretion of Sodium (FENa)": "fena",
    "Sequential Organ Failure Assessment (SOFA) Score": "sofa",
    "LDL Calculated": "ldl calculator",
    "CURB-65 Score for Pneumonia Severity": "curb-65",
    "Framingham Risk Score for Hard Coronary Heart Disease": "framingham risk score",
    "PERC Rule for Pulmonary Embolism": "perc rule",
    "Morphine Milligram Equivalents (MME) Calculator": "mme conversion",
    "SIRS Criteria": "sirs criteria",
    "QTc Fridericia Calculator": "qtc fridericia calculator",
    "QTc Framingham Calculator": "qtc framingham calculator",
    "QTc Hodges Calculator": "qtc hodges calculator",
    "QTc Rautaharju Calculator": "qtc rautaharju calculator",
    "Body Surface Area Calculator": "bmi",  # Uses BMI calculator
    "Target weight": "bmi",  # Uses BMI calculator
    "Adjusted Body Weight": "bmi",  # Uses BMI calculator
    "Delta Gap": "anion gap",  # Uses anion gap calculator
    "Delta Ratio": "anion gap",  # Uses anion gap calculator
    "Albumin Corrected Anion Gap": "anion gap",  # Uses anion gap calculator
    "Albumin Corrected Delta Gap": "anion gap",  # Uses anion gap calculator
    "Albumin Corrected Delta Ratio": "anion gap",  # Uses anion gap calculator
    "Estimated of Conception": None,  # Not in MDApp
    "Estimated Gestational Age": None,  # Not in MDApp
}


def get_calculator_url(calculator_name, mdapp_mappings):
    """Get URL for a calculator using the MDApp mappings"""
    short_name = FULL_NAME_TO_SHORT.get(calculator_name)
    
    if short_name is None:
        return None
    
    # Try exact match first
    if short_name.lower() in mdapp_mappings:
        return mdapp_mappings[short_name.lower()]
    
    # Try partial match
    for key, url in mdapp_mappings.items():
        if short_name.lower() in key.lower() or key.lower() in short_name.lower():
            return url
    
    return None


async def main():
    """Run remaining benchmarks sequentially with visible browser"""
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY='your-key'\n")
        return
    
    # Load MDApp mappings from the provided CSV
    mdapp_csv_path = "/Users/nikhilkhandekar/Downloads/Calculator Websites - MDApp - Sheet1.csv"
    if not os.path.exists(mdapp_csv_path):
        print(f"❌ ERROR: MDApp CSV file not found at {mdapp_csv_path}")
        return
    
    mdapp_mappings = load_mdapp_mappings(mdapp_csv_path)
    print(f"📋 Loaded {len(mdapp_mappings)} MDApp URL mappings from CSV")
    
    # Load previous results to continue from
    previous_results_file = "benchmark_results_simple_20251203_030237.json"
    previous_results = None
    completed_calculators = set()
    
    if os.path.exists(previous_results_file):
        with open(previous_results_file, 'r') as f:
            previous_results = json.load(f)
        completed_calculators = set(r['calculator'] for r in previous_results['results'])
        print(f"📊 Found previous run with {len(previous_results['results'])} completed tests")
        print(f"   Calculators completed: {len(completed_calculators)}")
    
    print("="*70)
    print("  Simple Sequential Benchmark Runner - CONTINUATION")
    print("  Visible browser • Only MDApp CSV mappings • Remaining tests")
    print("="*70)
    print()
    
    # Load test data
    print("📊 Loading test data...")
    if not os.path.exists('test_data_sampled_3_per_calc.csv'):
        print("  Creating sampled dataset...")
        os.system('python sample_by_calculator.py')
    
    with open('test_data_sampled_3_per_calc.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_test_cases = list(reader)
    
    # Filter to only remaining tests (calculators not in completed set)
    test_cases = [row for row in all_test_cases if row['Calculator Name'] not in completed_calculators]
    
    print(f"  Total test cases: {len(all_test_cases)}")
    print(f"  Already completed: {len(all_test_cases) - len(test_cases)}")
    print(f"  Remaining to run: {len(test_cases)}")
    print()
    
    if len(test_cases) == 0:
        print("✅ All tests already completed!")
        return
    
    # Initialize stats (continue from previous)
    stats = {
        "total": previous_results['stats']['total'] if previous_results else 0,
        "passed": previous_results['stats']['passed'] if previous_results else 0,
        "failed": previous_results['stats']['failed'] if previous_results else 0,
        "errors": previous_results['stats']['errors'] if previous_results else 0,
        "skipped": previous_results['stats']['skipped'] if previous_results else 0,
        "by_calculator": {}
    }
    results = previous_results['results'] if previous_results else []
    
    # Create LLM instance (reused)
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    # Create timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"benchmark_results_simple_{timestamp}.json"
    
    # Calculate starting index
    start_idx = len(all_test_cases) - len(test_cases) + 1
    
    # Run each remaining test
    for i, row in enumerate(test_cases, start_idx):
        calculator_name = row["Calculator Name"]
        url = get_calculator_url(calculator_name, mdapp_mappings)
        
        print(f"\n[{i}/{len(all_test_cases)}] {calculator_name}")
        
        if not url:
            print(f"  ⏭️ SKIPPED - No MDApp URL in CSV")
            stats["skipped"] += 1
            continue
        
        print(f"  🔗 URL: {url}")
        ground_truth = row["Ground Truth Answer"]
        patient_note = row.get("Patient Note", "")
        question = row.get("Question", "")
        
        # Create task with patient note - LLM must extract entities itself
        task_parts = [
            f"You are a medical AI assistant testing a web calculator.",
            f"",
            f"PATIENT NOTE:",
            f"{patient_note}",
            f"",
            f"QUESTION:",
            f"{question}",
            f"",
            f"CRITICAL RULES:",
            f"DO NOT calculate or compute the answer yourself, you MUST use the web calculator to get the answer.",
            f"Your answer will be marked as incorrect if you do this otherwise.",
            f"",
            f"TASK:",
            f"1. Navigate to {url}",
            f"2. Read the patient note and extract the relevant clinical values",
            f"3. Fill out the ENTIRE calculator form with the values from the note",
            f"4. Click the Calculate button on the webpage",
            f"5. Wait for the result to appear on the page",
            f"6. Extract ONLY the numerical result that the CALCULATOR computed (not your own calculation)",
            f"",
            f"IMPORTANT - Final Response Format:",
            f'After the calculator displays its result, return ONLY this JSON:',
            f'{{"answer": <number_from_calculator>}}',
            f"",
            f"Examples:",
            f'- {{"answer": 83.94}}',
            f'- {{"answer": 12}}',
            f'- {{"answer": 2.5}}',
            f"",
            f"The answer MUST be the value the web calculator computed, NOT a value you calculated yourself."
        ]
        
        task = "\n".join(task_parts)
        
        # Create fresh browser for this test
        print(f"  🌐 Starting fresh browser...")
        browser = Browser(
            headless=False,
            window_size={'width': 1920, 'height': 1080}
        )
        
        # Create file paths for this test
        safe_name = calculator_name.replace('/', '-').replace(' ', '_')[:50]
        trajectory_path = TRAJECTORY_DIR / f"{i:03d}_{safe_name}_{timestamp}.json"
        log_path = LOGS_DIR / f"{i:03d}_{safe_name}_{timestamp}.log"
        
        # Set up logging to file for this test
        file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Add handler to root logger and browser_use loggers
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
        
        try:
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                max_actions_per_step=10,
                use_vision=True,  # Enable vision for better form interaction
                save_conversation_path=str(trajectory_path)  # Save full trajectory
            )
            
            history = await agent.run(max_steps=30)
            result = history.final_result()
            
            # Copy the last vision screenshot
            screenshot_path = None
            try:
                screenshot_filename = f"{i:03d}_{safe_name}_{timestamp}.png"
                screenshot_path = SCREENSHOT_DIR / screenshot_filename
                
                # Get vision screenshots from agent history
                screenshots = history.screenshot_paths()
                if screenshots and len(screenshots) > 0:
                    last_screenshot = screenshots[-1]
                    if os.path.exists(last_screenshot):
                        shutil.copy2(last_screenshot, screenshot_path)
                        print(f"  📸 Screenshot: {screenshot_path.name}")
                    else:
                        print(f"  ⚠️ Screenshot file not found")
                else:
                    print(f"  ⚠️ No screenshots in history")
            except Exception as e:
                print(f"  ⚠️ Screenshot error: {str(e)[:80]}")
            
            print(f"  📝 Trajectory saved: {trajectory_path.name}")
            
            # Parse JSON response from agent
            agent_answer = None
            final_json = None
            
            try:
                # Try to parse as JSON first
                result_str = str(result).strip()
                
                # Extract JSON if embedded in text
                json_match = re.search(r'\{[^}]*"answer"[^}]*\}', result_str)
                if json_match:
                    final_json = json.loads(json_match.group())
                    agent_answer = final_json.get("answer")
                else:
                    # Try parsing entire result as JSON
                    final_json = json.loads(result_str)
                    agent_answer = final_json.get("answer")
            except (json.JSONDecodeError, AttributeError):
                # Fallback: extract number from text
                try:
                    numbers = re.findall(r'-?\d+\.?\d*', result_str)
                    if numbers:
                        agent_answer = float(numbers[0])
                except:
                    agent_answer = result_str
            
            # Compare results
            try:
                agent_num = float(agent_answer) if agent_answer is not None else None
                truth_num = float(ground_truth)
                
                if agent_num is None:
                    print(f"  ❌ FAILED - No answer extracted from: {str(result)[:50]}")
                    stats["failed"] += 1
                    results.append({
                        "calculator": calculator_name,
                        "status": "failed",
                        "ground_truth": truth_num,
                        "result": str(result),
                        "agent_json": final_json,
                        "steps": history.number_of_steps(),
                        "screenshot": str(screenshot_path) if screenshot_path else None,
                        "trajectory": str(trajectory_path),
                        "log": str(log_path)
                    })
                else:
                    tolerance = 0.05 * abs(truth_num) if truth_num != 0 else 0.05
                    is_correct = abs(agent_num - truth_num) <= tolerance
                    
                    if is_correct:
                        print(f"  ✅ PASSED - Got {agent_num}, expected {truth_num}")
                        stats["passed"] += 1
                    else:
                        print(f"  ❌ FAILED - Got {agent_num}, expected {truth_num}")
                        stats["failed"] += 1
                    
                    results.append({
                        "calculator": calculator_name,
                        "status": "passed" if is_correct else "failed",
                        "ground_truth": truth_num,
                        "result": agent_num,
                        "agent_json": final_json,
                        "raw_response": str(result),
                        "steps": history.number_of_steps(),
                        "screenshot": str(screenshot_path) if screenshot_path else None,
                        "trajectory": str(trajectory_path),
                        "log": str(log_path)
                    })
                
            except (ValueError, TypeError) as e:
                print(f"  ❌ FAILED - Could not parse result: {result}")
                stats["failed"] += 1
                results.append({
                    "calculator": calculator_name,
                    "status": "failed",
                    "ground_truth": ground_truth,
                    "result": str(result),
                    "agent_json": final_json,
                    "steps": history.number_of_steps(),
                    "screenshot": str(screenshot_path) if screenshot_path else None,
                    "trajectory": str(trajectory_path),
                    "log": str(log_path)
                })
            
            stats["total"] += 1
            
        except Exception as e:
            print(f"  ⚠️ ERROR - {str(e)[:100]}")
            stats["errors"] += 1
            stats["total"] += 1
            results.append({
                "calculator": calculator_name,
                "status": "error",
                "error": str(e),
                "screenshot": None,
                "trajectory": str(trajectory_path) if 'trajectory_path' in locals() else None,
                "log": str(log_path) if 'log_path' in locals() else None
            })
        
        finally:
            # Remove the log file handler
            if 'file_handler' in locals():
                file_handler.close()
                root_logger.removeHandler(file_handler)
                print(f"  📋 Log saved: {log_path.name}")
            
            # Always close and cleanup browser after each test
            try:
                if 'browser' in locals():
                    print(f"  🔄 Closing browser...")
                    await browser.close()
                    # Small delay to ensure cleanup
                    await asyncio.sleep(1)
            except Exception as cleanup_error:
                print(f"  ⚠️ Cleanup warning: {str(cleanup_error)[:50]}")
            
            # Save results after each iteration
            with open(results_file, 'w') as f:
                json.dump({
                    "stats": stats,
                    "results": results,
                    "timestamp": timestamp
                }, f, indent=2)
            print(f"  💾 Progress saved ({stats['total']} tests)")
    
    # Save final results
    with open(results_file, 'w') as f:
        json.dump({
            "stats": stats,
            "results": results,
            "timestamp": timestamp
        }, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 BENCHMARK SUMMARY")
    print("="*70)
    
    total = stats["total"]
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed:   {stats['passed']} ({stats['passed']/total*100:.1f}%)" if total > 0 else "✅ Passed: 0")
    print(f"❌ Failed:   {stats['failed']} ({stats['failed']/total*100:.1f}%)" if total > 0 else "❌ Failed: 0")
    print(f"⚠️ Errors:   {stats['errors']} ({stats['errors']/total*100:.1f}%)" if total > 0 else "⚠️ Errors: 0")
    print(f"⏭️ Skipped:  {stats['skipped']}")
    
    print(f"\n📁 Results saved to: {results_file}")
    print(f"📸 Screenshots saved to: {SCREENSHOT_DIR}/")
    print(f"📝 Trajectories saved to: {TRAJECTORY_DIR}/")
    print(f"📋 Logs saved to: {LOGS_DIR}/")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())

