"""
Simple sequential benchmark runner - no parallelization, visible browser
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

# Calculator name to MDApp URL mapping
CALCULATOR_MAPPING = {
    "Creatinine Clearance (Cockcroft-Gault Equation)": "https://www.mdapp.co/creatinine-clearance-calculator-38/",
    "CKD-EPI Equations for Glomerular Filtration Rate": "https://www.mdapp.co/gfr-calculator-17/",
    "CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk": "https://www.mdapp.co/cha2ds2-vasc-score-for-stroke-risk-in-atrial-fibrillation-141/",
    "Mean Arterial Pressure (MAP)": "https://www.mdapp.co/mean-arterial-pressure-calculator-122/",
    "Body Mass Index (BMI)": "https://www.mdapp.co/bmi-calculator-64/",
    "Calcium Correction for Hypoalbuminemia": "https://www.mdapp.co/hypoalbuminemia-corrected-calcium-calculator-103/",
    "Wells' Criteria for Pulmonary Embolism": "https://www.mdapp.co/wells-criteria-for-pulmonary-embolism-calculator-117/",
    "MDRD GFR Equation": "https://www.mdapp.co/mdrd-calculator-320/",
    "Ideal Body Weight": "https://www.mdapp.co/bmi-calculator-64/",  # Using BMI calculator
    "QTc Bazett Calculator": "https://www.mdapp.co/qtc-calculator-57/",
    "Estimated Due Date": None,  # Not available on MDApp
    "Child-Pugh Score for Cirrhosis Mortality": "https://www.mdapp.co/child-pugh-score-calculator-106/",
    "Wells' Criteria for DVT": "https://www.mdapp.co/wells-score-for-dvt-calculator-121/",
    "Revised Cardiac Risk Index for Pre-Operative Risk": "https://www.mdapp.co/revised-cardiac-risk-index-rcri-calculator-190/",
    "HEART Score for Major Cardiac Events": None,  # Not available on MDApp
    "Fibrosis-4 (FIB-4) Index for Liver Fibrosis": "https://www.mdapp.co/fibrosis-4-fib-4-score-calculator-107/",
    "Centor Score (Modified/McIsaac) for Strep Pharyngitis": "https://www.mdapp.co/strep-pharyngitis-centor-score-calculator-269/",
    "Glasgow Coma Score (GCS)": None,  # Not in MDApp CSV
    "Maintenance Fluids Calculations": "https://www.mdapp.co/iv-maintenance-fluids-calculator-307/",
    "MELD Na (UNOS/OPTN)": "https://www.mdapp.co/meld-na-score-calculator-174/",
    "Steroid Conversion Calculator": "https://www.mdapp.co/steroid-conversion-calculator-282/",
    "HAS-BLED Score for Major Bleeding Risk": "https://www.mdapp.co/has-bled-score-calculator-155/",
    "Sodium Correction for Hyperglycemia": "https://www.mdapp.co/corrected-sodium-calculator-477/",
    "Glasgow-Blatchford Bleeding Score (GBS)": "https://www.mdapp.co/glasgow-blatchford-score-gbs-calculator-161/",
    "APACHE II Score": "https://www.mdapp.co/apache-ii-score-calculator-158/",
    "PSI Score: Pneumonia Severity Index for CAP": "https://www.mdapp.co/pneumonia-severity-index-psi-calculator-247/",
    "Serum Osmolality": "https://www.mdapp.co/serum-osmolality-calculator-74/",
    "HOMA-IR (Homeostatic Model Assessment for Insulin Resistance)": "https://www.mdapp.co/homa-ir-calculator-for-insulin-resistance-482/",
    "Charlson Comorbidity Index (CCI)": "https://www.mdapp.co/charlson-comorbidity-index-cci-calculator-131/",
    "FeverPAIN Score for Strep Pharyngitis": "https://www.mdapp.co/feverpain-score-calculator-494/",
    "Caprini Score for Venous Thromboembolism (2005)": "https://www.mdapp.co/caprini-score-for-dvt-risk-calculator-405/",
    "Free Water Deficit": "https://www.mdapp.co/free-water-deficit-calculator-126/",
    "Anion Gap": "https://www.mdapp.co/anion-gap-calculator-92/",
    "Fractional Excretion of Sodium (FENa)": "https://www.mdapp.co/fena-calculator-44/",
    "Sequential Organ Failure Assessment (SOFA) Score": "https://www.mdapp.co/sequential-organ-failure-assessment-sofa-score-calculator-184/",
    "LDL Calculated": "https://www.mdapp.co/ldl-calculator-96/",
    "CURB-65 Score for Pneumonia Severity": "https://www.mdapp.co/pneumonia-curb-65-score-calculator-151/",
    "Framingham Risk Score for Hard Coronary Heart Disease": "https://www.mdapp.co/framingham-risk-score-calculator-123/",
    "PERC Rule for Pulmonary Embolism": "https://www.mdapp.co/perc-rule-calculator-116/",
    "Morphine Milligram Equivalents (MME) Calculator": "https://www.mdapp.co/steroid-conversion-calculator-282/",  # Note: using steroid converter
    "SIRS Criteria": None,  # Not available on MDApp
    "QTc Fridericia Calculator": "https://www.mdapp.co/qtc-calculator-57/",
    "QTc Framingham Calculator": "https://www.mdapp.co/qtc-calculator-57/",
    "QTc Hodges Calculator": "https://www.mdapp.co/qtc-calculator-57/",
    "QTc Rautaharju Calculator": "https://www.mdapp.co/qtc-calculator-57/",
    "Body Surface Area Calculator": "https://www.mdapp.co/bmi-calculator-64/",  # Using BMI calculator
    "Target weight": "https://www.mdapp.co/bmi-calculator-64/",
    "Adjusted Body Weight": "https://www.mdapp.co/bmi-calculator-64/",
    "Delta Gap": "https://www.mdapp.co/anion-gap-calculator-92/",
    "Delta Ratio": "https://www.mdapp.co/anion-gap-calculator-92/",
    "Albumin Corrected Anion Gap": "https://www.mdapp.co/anion-gap-calculator-92/",
    "Albumin Corrected Delta Gap": "https://www.mdapp.co/anion-gap-calculator-92/",
    "Albumin Corrected Delta Ratio": "https://www.mdapp.co/anion-gap-calculator-92/",
    "Estimated of Conception": None,  # Not available on MDApp
    "Estimated Gestational Age": None,  # Not available on MDApp
}


async def main():
    """Run all benchmarks sequentially with visible browser"""
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY='your-key'\n")
        return
    
    print("="*70)
    print("  Simple Sequential Benchmark Runner")
    print("  Visible browser • No parallelization • All 165 tests")
    print("="*70)
    print()
    
    # Sample and load test data
    print("📊 Loading test data...")
    if not os.path.exists('test_data_sampled_3_per_calc.csv'):
        print("  Creating sampled dataset...")
        os.system('python sample_by_calculator.py')
    
    with open('test_data_sampled_3_per_calc.csv', 'r', encoding='utf-8') as f:
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
        "by_calculator": {}
    }
    results = []
    
    # Create LLM instance (reused)
    llm = ChatOpenAI(model="gpt-5-mini")
    
    # Create timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"benchmark_results_simple_{timestamp}.json"
    
    # Run each test
    for i, row in enumerate(test_cases, 1):
        calculator_name = row["Calculator Name"]
        url = CALCULATOR_MAPPING.get(calculator_name)
        
        print(f"\n[{i}/{len(test_cases)}] {calculator_name}")
        
        if not url:
            print(f"  ⏭️ SKIPPED - No MDApp URL available")
            stats["skipped"] += 1
            continue
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
        
        # Create fresh browser for this test - use Microsoft Edge
        print(f"  🌐 Starting fresh browser (Microsoft Edge)...")
        browser = Browser(
            headless=False,
            window_size={'width': 1920, 'height': 1080},
            executable_path='/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
            disable_security=True,
            minimum_wait_page_load_time=0.1,
            wait_for_network_idle_page_load_time=0.25,
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
                use_thinking=False,  # Disable thinking to avoid timeouts
                llm_timeout=120,  # Increase timeout to 120 seconds
                save_conversation_path=str(trajectory_path)  # Save full trajectory
            )
            
            history = await agent.run(max_steps=30)
            result = history.final_result()
            
            # Copy the last vision screenshot (now full-page thanks to browser-use modification)
            screenshot_path = None
            try:
                screenshot_filename = f"{i:03d}_{safe_name}_{timestamp}.png"
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
                    tolerance = 0.05 * abs(truth_num)
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
                    if hasattr(browser, 'close'):
                        await browser.close()
                    elif hasattr(browser, 'context') and hasattr(browser.context, 'close'):
                        await browser.context.close()
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

