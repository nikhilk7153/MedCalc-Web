"""
Simple sequential benchmark runner - no parallelization, visible browser
"""
import asyncio
import csv
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Create screenshots directory
SCREENSHOT_DIR = Path("benchmark_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Calculator name to HTML file mapping
CALCULATOR_MAPPING = {
    "Creatinine Clearance (Cockcroft-Gault Equation)": "creatinine-clearance.html",
    "CKD-EPI Equations for Glomerular Filtration Rate": "ckd-epi.html",
    "CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk": "cha2ds2-vasc.html",
    "Mean Arterial Pressure (MAP)": "mean-arterial-pressure.html",
    "Body Mass Index (BMI)": "body-weight-suite.html",
    "Calcium Correction for Hypoalbuminemia": "calcium-correction.html",
    "Wells' Criteria for Pulmonary Embolism": "wells-pe.html",
    "MDRD GFR Equation": "mdrd-gfr.html",
    "Ideal Body Weight": "body-weight-suite.html",
    "QTc Bazett Calculator": "qtc.html",
    "Estimated Due Date": "estimated-due-date.html",
    "Child-Pugh Score for Cirrhosis Mortality": "child-pugh.html",
    "Wells' Criteria for DVT": "wells-dvt.html",
    "Revised Cardiac Risk Index for Pre-Operative Risk": "cardiac-risk-index.html",
    "HEART Score for Major Cardiac Events": "heart-score.html",
    "Fibrosis-4 (FIB-4) Index for Liver Fibrosis": "fibrosis-4.html",
    "Centor Score (Modified/McIsaac) for Strep Pharyngitis": "centor-score.html",
    "Glasgow Coma Score (GCS)": "glasgow-coma-score.html",
    "Maintenance Fluids Calculations": "maintenance-fluids.html",
    "MELD Na (UNOS/OPTN)": "meld-na.html",
    "Steroid Conversion Calculator": "steroid-conversion.html",
    "HAS-BLED Score for Major Bleeding Risk": "has-bled.html",
    "Sodium Correction for Hyperglycemia": "sodium-correction.html",
    "Glasgow-Blatchford Bleeding Score (GBS)": "glasgow-blatchford.html",
    "APACHE II Score": "apache-ii.html",
    "PSI Score: Pneumonia Severity Index for CAP": "psi.html",
    "Serum Osmolality": "serum-osmolality.html",
    "HOMA-IR (Homeostatic Model Assessment for Insulin Resistance)": "homa-ir.html",
    "Charlson Comorbidity Index (CCI)": "charlson-cci.html",
    "FeverPAIN Score for Strep Pharyngitis": "feverpain.html",
    "Caprini Score for Venous Thromboembolism (2005)": "caprini.html",
    "Free Water Deficit": "free-water-deficit.html",
    "Anion Gap": "anion-gap.html",
    "Fractional Excretion of Sodium (FENa)": "fena.html",
    "Sequential Organ Failure Assessment (SOFA) Score": "sofa.html",
    "LDL Calculated": "ldl-calculated.html",
    "CURB-65 Score for Pneumonia Severity": "curb-65.html",
    "Framingham Risk Score for Hard Coronary Heart Disease": "framingham-risk.html",
    "PERC Rule for Pulmonary Embolism": "perc-rule.html",
    "Morphine Milligram Equivalents (MME) Calculator": "mme.html",
    "SIRS Criteria": "sirs.html",
    "QTc Fridericia Calculator": "qtc.html",
    "QTc Framingham Calculator": "qtc.html",
    "QTc Hodges Calculator": "qtc.html",
    "QTc Rautaharju Calculator": "qtc.html",
    "Body Surface Area Calculator": "body-weight-suite.html",
    "Target weight": "body-weight-suite.html",
    "Adjusted Body Weight": "body-weight-suite.html",
    "Delta Gap": "anion-gap.html",
    "Delta Ratio": "anion-gap.html",
    "Albumin Corrected Anion Gap": "anion-gap.html",
    "Albumin Corrected Delta Gap": "anion-gap.html",
    "Albumin Corrected Delta Ratio": "anion-gap.html",
    "Estimated of Conception": "estimated-conception.html",
    "Estimated Gestational Age": "gestational-age.html"
}

BASE_URL = "http://localhost:8000"


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
    
    # Run each test
    for i, row in enumerate(test_cases, 1):
        calculator_name = row["Calculator Name"]
        html_file = CALCULATOR_MAPPING.get(calculator_name)
        
        print(f"\n[{i}/{len(test_cases)}] {calculator_name}")
        
        if not html_file:
            print(f"  ⏭️ SKIPPED - No HTML mapping")
            stats["skipped"] += 1
            continue
        
     
        
        url = f"{BASE_URL}/{html_file}"
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
            headless=False,  # Show browser window
            window_size={'width': 1400, 'height': 1200}
        )
        
        try:
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                max_actions_per_step=10,
                use_vision=True,  # Enable vision for better form interaction
                use_thinking=False,  # Disable thinking to avoid timeouts
                llm_timeout=120  # Increase timeout to 120 seconds
            )
            
            history = await agent.run(max_steps=30)
            result = history.final_result()
            
            # Take webpage screenshot after test completes  
            screenshot_path = None
            try:
                await asyncio.sleep(2)  # Wait for result to display
                
                safe_name = calculator_name.replace('/', '-').replace(' ', '_')[:50]
                screenshot_filename = f"{i:03d}_{safe_name}_{timestamp}.png"
                screenshot_path = SCREENSHOT_DIR / screenshot_filename
                
                # Access Playwright page - browser IS the session
                page = browser.context.pages[0]
                await page.screenshot(path=str(screenshot_path), full_page=True)
                    
                print(f"  📸 Screenshot: {screenshot_path.name}")
            except Exception as e:
                print(f"  ⚠️ Screenshot error: {str(e)[:80]}")
            
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
                        "screenshot": str(screenshot_path) if screenshot_path else None
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
                        "screenshot": str(screenshot_path) if screenshot_path else None
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
                    "screenshot": str(screenshot_path) if screenshot_path else None
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
                "screenshot": None
            })
        
        finally:
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
    
    # Save results
    results_file = f"benchmark_results_simple_{timestamp}.json"
    
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
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())

