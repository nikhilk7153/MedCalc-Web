"""
Simple sequential benchmark runner - no parallelization, visible browser
"""
import asyncio
import csv
import json
import os
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
    
    # Create single browser instance
    print("🌐 Starting browser (visible mode)...")
    browser = Browser(
        headless=False,  # Show browser window
        window_size={'width': 1400, 'height': 1000}
    )
    
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
        
        # Parse entities
        try:
            entities = eval(row["Relevant Entities"])
        except Exception as e:
            print(f"  ⚠️ ERROR - Failed to parse entities: {str(e)}")
            stats["errors"] += 1
            stats["total"] += 1
            continue
        
        url = f"{BASE_URL}/{html_file}"
        ground_truth = row["Ground Truth Answer"]
        patient_note = row.get("Patient Note", "")
        question = row.get("Question", "")
        
        # Create task with patient note - LLM must extract entities itself
        task_parts = [
            f"You are a medical AI assistant.",
            f"",
            f"PATIENT NOTE:",
            f"{patient_note}",
            f"",
            f"QUESTION:",
            f"{question}",
            f"",
            f"TASK:",
            f"1. Navigate to {url}",
            f"2. Read the patient note carefully and extract the relevant clinical values",
            f"3. Fill out the calculator form using the values you extracted from the note",
            f"4. Click the Calculate button",
            f"5. Extract the numerical result from the page",
            f"6. Return ONLY the final numerical answer without any units or explanation"
        ]
        
        task = "\n".join(task_parts)
        
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
            
            # Save final screenshot
            screenshot_path = None
            try:
                # Get screenshots from history
                screenshots = history.screenshot_paths()
                if screenshots:
                    # Copy the last screenshot to our directory
                    last_screenshot = screenshots[-1]
                    if os.path.exists(last_screenshot):
                        safe_name = calculator_name.replace('/', '-').replace(' ', '_')[:50]
                        screenshot_filename = f"{i:03d}_{safe_name}_{timestamp}.png"
                        screenshot_path = SCREENSHOT_DIR / screenshot_filename
                        shutil.copy2(last_screenshot, screenshot_path)
                        print(f"  📸 Screenshot saved: {screenshot_path.name}")
            except Exception as e:
                print(f"  ⚠️ Could not save screenshot: {str(e)[:50]}")
            
            # Compare results
            try:
                agent_num = float(str(result).strip())
                truth_num = float(ground_truth)
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
                    "steps": history.number_of_steps(),
                    "screenshot": str(screenshot_path) if screenshot_path else None
                })
                
            except (ValueError, TypeError):
                print(f"  ❌ FAILED - Could not parse result: {result}")
                stats["failed"] += 1
                results.append({
                    "calculator": calculator_name,
                    "status": "failed",
                    "ground_truth": ground_truth,
                    "result": str(result),
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
                "error": str(e)
            })
    
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

