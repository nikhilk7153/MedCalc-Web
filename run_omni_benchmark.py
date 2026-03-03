"""
Simple sequential benchmark runner for Omni Calculator - same format as run_simple_benchmark.py
"""
import asyncio
import csv
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from browser_use import Agent, Browser, ChatOpenAI, ChatGoogle
from dotenv import load_dotenv

from benchmark_evaluation import evaluate_prediction, parse_agent_result

load_dotenv()

# Directories will be created with timestamps in main()

# Calculator name to Omni Calculator URL mapping (from Calculator Websites - Omni Calculator.csv)
CALCULATOR_MAPPING = {
    "Creatinine Clearance (Cockcroft-Gault Equation)": "https://www.omnicalculator.com/health/crcl",
    "CKD-EPI Equations for Glomerular Filtration Rate": None,  # Not available
    "CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk": "https://www.omnicalculator.com/health/cha2ds2-vasc",
    "Mean Arterial Pressure (MAP)": "https://www.omnicalculator.com/health/mean-arterial-pressure",
    "Body Mass Index (BMI)": "https://www.omnicalculator.com/health/bmi",
    "Calcium Correction for Hypoalbuminemia": "https://www.omnicalculator.com/health/corrected-calcium",
    "Wells' Criteria for Pulmonary Embolism": "https://www.omnicalculator.com/health/wells-pe",
    "MDRD GFR Equation": "https://www.omnicalculator.com/health/glomerular-filtration-rate",
    "Ideal Body Weight": "https://www.omnicalculator.com/health/ideal-weight",
    "QTc Bazett Calculator": "https://www.omnicalculator.com/health/qtc",
    "Estimated Due Date": "https://www.omnicalculator.com/health/pregnancy-due-date",
    "Child-Pugh Score for Cirrhosis Mortality": "https://www.omnicalculator.com/health/child-pugh",
    "Wells' Criteria for DVT": None,  # Not available
    "Revised Cardiac Risk Index for Pre-Operative Risk": "https://www.omnicalculator.com/health/rcri",
    "HEART Score for Major Cardiac Events": "https://www.omnicalculator.com/health/heart-score",
    "Fibrosis-4 (FIB-4) Index for Liver Fibrosis": "https://www.omnicalculator.com/health/fib-4",
    "Centor Score (Modified/McIsaac) for Strep Pharyngitis": "https://www.omnicalculator.com/health/centor",
    "Glasgow Coma Score (GCS)": "https://www.omnicalculator.com/health/gcs",
    "Maintenance Fluids Calculations": "https://www.omnicalculator.com/health/maintenance-fluids-children",
    "MELD Na (UNOS/OPTN)": None,  # Not available
    "Steroid Conversion Calculator": "https://www.omnicalculator.com/health/steroid",
    "HAS-BLED Score for Major Bleeding Risk": "https://www.omnicalculator.com/health/has-bled",
    "Sodium Correction for Hyperglycemia": None,  # Not available
    "Glasgow-Blatchford Bleeding Score (GBS)": None,  # Not available
    "APACHE II Score": "https://www.omnicalculator.com/health/apache-ii",
    "PSI Score: Pneumonia Severity Index for CAP": "https://www.omnicalculator.com/health/psi",
    "Serum Osmolality": "https://www.omnicalculator.com/health/serum-osmolality",
    "HOMA-IR (Homeostatic Model Assessment for Insulin Resistance)": "https://www.omnicalculator.com/health/homa-ir",
    "Charlson Comorbidity Index (CCI)": "https://www.omnicalculator.com/health/cci",
    "FeverPAIN Score for Strep Pharyngitis": None,  # Not available
    "Caprini Score for Venous Thromboembolism (2005)": None,  # Not available
    "Free Water Deficit": "https://www.omnicalculator.com/health/water-deficit",
    "Anion Gap": "https://www.omnicalculator.com/health/anion-gap",
    "Fractional Excretion of Sodium (FENa)": "https://www.omnicalculator.com/health/fena",
    "Sequential Organ Failure Assessment (SOFA) Score": "https://www.omnicalculator.com/health/sofa-score",
    "LDL Calculated": "https://www.omnicalculator.com/health/ldl",
    "CURB-65 Score for Pneumonia Severity": "https://www.omnicalculator.com/health/curb",
    "Framingham Risk Score for Hard Coronary Heart Disease": "https://www.omnicalculator.com/health/framingham-risk",
    "PERC Rule for Pulmonary Embolism": "https://www.omnicalculator.com/health/perc",
    "Morphine Milligram Equivalents (MME) Calculator": None,  # Not available
    "SIRS Criteria": None,  # Not available
    "QTc Fridericia Calculator": "https://www.omnicalculator.com/health/qtc",
    "QTc Framingham Calculator": "https://www.omnicalculator.com/health/qtc",
    "QTc Hodges Calculator": "https://www.omnicalculator.com/health/qtc",
    "QTc Rautaharju Calculator": None,  # Not available
    "Body Surface Area Calculator": None,  # Not available
    "Target weight": None,  # Not available
    "Adjusted Body Weight": "https://www.omnicalculator.com/health/adjusted-weight",
    "Delta Gap": None,  # Not available
    "Delta Ratio": None,  # Not available
    "Albumin Corrected Anion Gap": None,  # Not available
    "Albumin Corrected Delta Gap": None,  # Not available
    "Albumin Corrected Delta Ratio": None,  # Not available
    "Estimated of Conception": None,  # Not available
    "Estimated Gestational Age": None,  # Not available
}


def _new_bucket() -> dict[str, int]:
    return {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}


def _update_bucket(container: dict[str, dict[str, int]], key: str, status: str) -> None:
    bucket = container.setdefault(key, _new_bucket())
    if status == "skipped":
        bucket["skipped"] += 1
        return

    bucket["total"] += 1
    if status in ("passed", "failed", "errors"):
        bucket[status] += 1


def _metrics_view(container: dict[str, dict[str, int]]) -> dict[str, dict[str, float | int | None]]:
    view: dict[str, dict[str, float | int | None]] = {}
    for key, bucket in container.items():
        total = bucket["total"]
        accuracy = (bucket["passed"] / total) if total > 0 else None
        view[key] = {
            "total": total,
            "passed": bucket["passed"],
            "failed": bucket["failed"],
            "errors": bucket["errors"],
            "skipped": bucket["skipped"],
            "end_to_end_accuracy": round(accuracy, 4) if accuracy is not None else None,
        }
    return view


async def main():
    """Run all benchmarks sequentially with visible browser"""
    
    # Set longer timeouts for Omni Calculator (pages are slow to load)
    os.environ['BROWSER_USE_PAGE_READINESS_TIMEOUT'] = '30.0'
    os.environ['BROWSER_USE_DOM_TIMEOUT'] = '60.0'
    os.environ['BROWSER_USE_SCREENSHOT_TIMEOUT'] = '30.0'
    os.environ['BROWSER_USE_AGENT_FOCUS_TIMEOUT'] = '30.0'
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY='your-key'\n")
        return
    
    print("="*70)
    print("  Omni Calculator Benchmark Runner")
    print("  Visible browser • No parallelization • All tests")
    print("="*70)
    print()
    
    # Sample and load test data
    print("📊 Loading test data...")
    if not os.path.exists('test_data_sampled_5_per_calc.csv'):
        print("  Dataset not found. Downloading from Hugging Face...")
        os.system('python download_and_sample_dataset.py')
    
    with open('test_data_sampled_5_per_calc.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        test_cases = list(reader)
    
    print(f"  Loaded {len(test_cases)} test cases\n")
    
    # Initialize stats
    stats = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "by_calculator": {},
        "by_category": {},
        "by_output_type": {},
    }
    results = []
    
    # Create LLM instance (reused)
    # Support both OpenAI and Gemini models
    model_name = os.getenv('LLM_MODEL', 'gpt-5-mini')
    if model_name.startswith('gemini'):
        llm = ChatGoogle(model=model_name)
    else:
        llm = ChatOpenAI(model=model_name)
    
    # Create timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create timestamped directories
    LOGS_DIR = Path(f"omni_benchmark_logs_{timestamp}")
    LOGS_DIR.mkdir(exist_ok=True)
    TRAJECTORY_DIR = Path(f"omni_benchmark_trajectories_{timestamp}")
    TRAJECTORY_DIR.mkdir(exist_ok=True)
    RESULTS_DIR = Path(f"omni_benchmark_results_{timestamp}")
    RESULTS_DIR.mkdir(exist_ok=True)
    
    # Create timestamped screenshot directory
    SCREENSHOT_DIR = LOGS_DIR / "screenshots" / f"trajectories_{timestamp}"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    results_file = RESULTS_DIR / f"omni_benchmark_results_{timestamp}.json"
    
    # Run each test
    for i, row in enumerate(test_cases, 1):
        calculator_name = row["Calculator Name"]
        url = CALCULATOR_MAPPING.get(calculator_name)
        calculator_id = row.get("Calculator ID", "")
        row_number = row.get("Row Number", str(i))
        category = row.get("Category", "unknown")
        output_type = row.get("Output Type", "unknown")
        lower_limit = row.get("Lower Limit")
        upper_limit = row.get("Upper Limit")
        
        print(f"\n[{i}/{len(test_cases)}] {calculator_name}")
        
        if not url:
            print(f"  ⏭️ SKIPPED - No Omni Calculator URL available")
            stats["skipped"] += 1
            _update_bucket(stats["by_calculator"], calculator_name, "skipped")
            _update_bucket(stats["by_category"], category, "skipped")
            _update_bucket(stats["by_output_type"], output_type, "skipped")
            results.append({
                "site": "omni",
                "row_number": row_number,
                "calculator_id": calculator_id,
                "calculator": calculator_name,
                "category": category,
                "output_type": output_type,
                "status": "skipped",
                "failure_type": "coverage_missing_target",
                "skip_reason": "no_omni_url_mapping",
            })
            continue
        ground_truth = row["Ground Truth Answer"]
        patient_note = row.get("Patient Note", "")
        # Override question for Calculator ID 2
        if calculator_id == "2":
            question = "What is the patient's Creatinine Clearance using the Cockroft-Gault Equation in terms of mL/min?"
        else:
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
            f"4. The calculator may auto-calculate or you may need to click a button",
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
            f'- {{"answer": 06/23/2021}}',
            f"",
            f"The answer MUST be the value the web calculator computed, NOT a value you calculated yourself."
        ]
        
        task = "\n".join(task_parts)
        
        # Create fresh browser for this test - use Chrome
        print(f"  🌐 Starting fresh browser (Chrome)...")
        chrome_path = '/opt/google/chrome/google-chrome'  # Use resolved Chrome path
        if not os.path.exists(chrome_path):
            chrome_path = '/usr/bin/google-chrome'  # Fallback to symlink
        browser = Browser(
            headless=False,
            executable_path=chrome_path,  # Explicitly use Chrome on Linux
            channel='chrome',  # Specify Chrome channel
            disable_security=True,  # Faster loading
            minimum_wait_page_load_time=0.1,  # Reduce wait time
            wait_for_network_idle_page_load_time=0.25,  # Reduce network idle wait
        )
        
        # Create file paths for this test
        safe_name = calculator_name.replace('/', '-').replace(' ', '_')
        trajectory_path = TRAJECTORY_DIR / f"{i:03d}_row{row_number}_{safe_name}_{timestamp}.json"
        log_path = LOGS_DIR / f"{i:03d}_row{row_number}_{safe_name}_{timestamp}.log"
        
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
                use_thinking=False,  # Disable thinking to avoid timeouts
                llm_timeout=120,  # Increase timeout to 120 seconds
                save_conversation_path=str(trajectory_path)  # Save full trajectory
            )
            
            wall_started = time.monotonic()
            history = await agent.run(max_steps=30)
            result = history.final_result()
            wall_seconds = round(time.monotonic() - wall_started, 3)
            
            # Copy the last vision screenshot (now full-page thanks to browser-use modification)
            screenshot_path = None
            try:
                screenshot_filename = f"{i:03d}_row{row_number}_{safe_name}_{timestamp}.png"
                screenshot_path = SCREENSHOT_DIR / screenshot_filename
                
                # Get vision screenshots from agent history (now full-page)
                screenshots = history.screenshot_paths()
                if screenshots and len(screenshots) > 0:
                    last_screenshot = screenshots[-1]
                    if os.path.exists(last_screenshot):
                        shutil.copy2(last_screenshot, screenshot_path)
                        print(f"  📸 Full-page screenshot: {screenshot_path.name}")
                    else:
                        print(f"  ⚠️ Screenshot file not found")
                else:
                    print(f"  ⚠️ No screenshots in history")
            except Exception as e:
                print(f"  ⚠️ Screenshot error: {str(e)}")
            
            print(f"  📝 Trajectory saved: {trajectory_path.name}")
            
            # Shared parser/scorer keeps MDApp/Omni/local runners aligned.
            parsed = parse_agent_result(result)
            scoring = evaluate_prediction(
                agent_answer=parsed["agent_answer"],
                ground_truth=ground_truth,
                output_type=output_type,
                lower_limit=lower_limit,
                upper_limit=upper_limit,
                raw_response=parsed["raw_response"],
                extraction_method=parsed["extraction_method"],
            )

            status = "passed" if scoring["is_correct"] else "failed"
            stats[status] += 1
            stats["total"] += 1
            _update_bucket(stats["by_calculator"], calculator_name, status)
            _update_bucket(stats["by_category"], category, status)
            _update_bucket(stats["by_output_type"], output_type, status)

            if scoring["is_correct"]:
                print(f"  ✅ PASSED - Got {scoring['normalized_prediction']}, expected {scoring['normalized_truth']}")
            else:
                print(f"  ❌ FAILED - Got {scoring['normalized_prediction']}, expected {scoring['normalized_truth']} ({scoring['failure_type']})")

            results.append({
                "site": "omni",
                "row_number": row_number,
                "calculator_id": calculator_id,
                "calculator": calculator_name,
                "category": category,
                "output_type": output_type,
                "status": status,
                "failure_type": scoring["failure_type"],
                "scoring_rule": scoring["scoring_rule"],
                "ground_truth": scoring["normalized_truth"],
                "result": scoring["normalized_prediction"],
                "lower_bound": scoring["lower_bound"],
                "upper_bound": scoring["upper_bound"],
                "raw_ground_truth": ground_truth,
                "raw_lower_limit": lower_limit,
                "raw_upper_limit": upper_limit,
                "agent_answer": parsed["agent_answer"],
                "agent_json": parsed["agent_json"],
                "raw_response": parsed["raw_response"],
                "extraction_method": parsed["extraction_method"],
                "timing": {
                    "wall_seconds": wall_seconds,
                    "agent_steps": history.number_of_steps(),
                    "llm_calls": None,
                    "total_tokens": None,
                },
                "screenshot": str(screenshot_path) if screenshot_path else None,
                "trajectory": str(trajectory_path),
                "log": str(log_path),
            })
            
        except Exception as e:
            print(f"  ⚠️ ERROR - {str(e)}")
            stats["errors"] += 1
            stats["total"] += 1
            _update_bucket(stats["by_calculator"], calculator_name, "errors")
            _update_bucket(stats["by_category"], category, "errors")
            _update_bucket(stats["by_output_type"], output_type, "errors")
            results.append({
                "site": "omni",
                "row_number": row_number,
                "calculator_id": calculator_id,
                "calculator": calculator_name,
                "category": category,
                "output_type": output_type,
                "status": "error",
                "failure_type": "runtime_exception",
                "error": str(e),
                "timing": {
                    "wall_seconds": None,
                    "agent_steps": None,
                    "llm_calls": None,
                    "total_tokens": None,
                },
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
                    if hasattr(browser, 'close'):
                        await browser.close()
                    elif hasattr(browser, 'context') and hasattr(browser.context, 'close'):
                        await browser.context.close()
                    # Small delay to ensure cleanup
                    await asyncio.sleep(1)
            except Exception as cleanup_error:
                print(f"  ⚠️ Cleanup warning: {str(cleanup_error)}")
            
            # Save results after each iteration
            with open(results_file, 'w') as f:
                json.dump({
                    "stats": stats,
                    "metrics_by_category": _metrics_view(stats["by_category"]),
                    "metrics_by_output_type": _metrics_view(stats["by_output_type"]),
                    "results": results,
                    "timestamp": timestamp
                }, f, indent=2)
            print(f"  💾 Progress saved ({stats['total']} tests)")
    
    # Save final results
    with open(results_file, 'w') as f:
        json.dump({
            "stats": stats,
            "metrics_by_category": _metrics_view(stats["by_category"]),
            "metrics_by_output_type": _metrics_view(stats["by_output_type"]),
            "results": results,
            "timestamp": timestamp
        }, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 OMNI CALCULATOR BENCHMARK SUMMARY")
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
