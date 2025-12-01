"""
Benchmarking script for MedCalc-Web calculators using browser-use
"""
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

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


class CalculatorBenchmark:
    def __init__(self, test_csv_path: str, max_tests: int = None):
        self.test_csv_path = test_csv_path
        self.max_tests = max_tests
        self.results = []
        self.stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "by_calculator": {}
        }
    
    async def run_single_test(self, row: dict, browser: Browser) -> dict:
        """Run a single calculator test"""
        calculator_name = row["Calculator Name"]
        html_file = CALCULATOR_MAPPING.get(calculator_name)
        
        if not html_file:
            return {
                "status": "skipped",
                "reason": f"No HTML mapping for {calculator_name}",
                "calculator": calculator_name
            }
        
        # Parse relevant entities (inputs)
        try:
            entities = eval(row["Relevant Entities"])  # Safe in this context
        except Exception as e:
            return {
                "status": "error",
                "reason": f"Failed to parse entities: {str(e)}",
                "calculator": calculator_name
            }
        
        url = f"{BASE_URL}/{html_file}"
        ground_truth = row["Ground Truth Answer"]
        
        # Create task for the agent
        task = self._create_task(calculator_name, url, entities, row.get("Question", ""))
        
        try:
            llm = ChatOpenAI(model="gpt-5-mini")
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                max_actions_per_step=10
            )
            
            history = await agent.run(max_steps=30)
            
            # Extract result from agent
            result = history.final_result()
            
            # Compare with ground truth
            is_correct = self._compare_results(result, ground_truth, row.get("Lower Limit"), row.get("Upper Limit"))
            
            return {
                "status": "passed" if is_correct else "failed",
                "calculator": calculator_name,
                "url": url,
                "ground_truth": ground_truth,
                "agent_result": result,
                "is_correct": is_correct,
                "steps": history.number_of_steps(),
                "duration": history.total_duration_seconds()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "calculator": calculator_name,
                "url": url,
                "error": str(e)
            }
    
    def _create_task(self, calculator_name: str, url: str, entities: dict, question: str) -> str:
        """Create a task string for the agent"""
        task_parts = [
            f"Navigate to {url}",
            "Fill out the calculator form with the following values:",
        ]
        
        # Add entity values
        for key, value in entities.items():
            if isinstance(value, list) and len(value) == 2:
                task_parts.append(f"- {key}: {value[0]} {value[1]}")
            else:
                task_parts.append(f"- {key}: {value}")
        
        task_parts.extend([
            "",
            "Then click the Calculate button.",
            "Extract the numerical result from the page.",
            "Return ONLY the final numerical answer without any units or explanation."
        ])
        
        return "\n".join(task_parts)
    
    def _compare_results(self, agent_result: str, ground_truth: str, lower_limit: str = None, upper_limit: str = None) -> bool:
        """Compare agent result with ground truth"""
        if not agent_result:
            return False
        
        try:
            # Extract numbers from strings
            agent_num = self._extract_number(str(agent_result))
            truth_num = float(ground_truth)
            
            if agent_num is None:
                return False
            
            # Check if within tolerance (5% or within limits if provided)
            tolerance = 0.05 * abs(truth_num)
            
            if lower_limit and upper_limit:
                lower = float(lower_limit)
                upper = float(upper_limit)
                return lower <= agent_num <= upper
            
            return abs(agent_num - truth_num) <= tolerance
            
        except (ValueError, TypeError):
            # Fallback to string comparison
            return str(agent_result).strip() == str(ground_truth).strip()
    
    def _extract_number(self, text: str) -> float:
        """Extract first number from text"""
        import re
        numbers = re.findall(r'-?\d+\.?\d*', text)
        if numbers:
            return float(numbers[0])
        return None
    
    async def run_benchmark(self):
        """Run the full benchmark"""
        print(f"🚀 Starting benchmark from {self.test_csv_path}")
        print(f"📊 Max tests: {self.max_tests if self.max_tests else 'all'}\n")
        
        # Check for API key
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ ERROR: OPENAI_API_KEY environment variable not set")
            print("Please set it with: export OPENAI_API_KEY='your-key'\n")
            return
        
        # Read test data
        with open(self.test_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            test_cases = list(reader)
        
        if self.max_tests:
            test_cases = test_cases[:self.max_tests]
        
        # Create browser instance
        browser = Browser(
            headless=True,  # Run headless for parallel execution
            window_size={'width': 1400, 'height': 1000}
        )
        
        # Run tests
        for i, row in enumerate(test_cases, 1):
            calculator = row["Calculator Name"]
            print(f"\n[{i}/{len(test_cases)}] Testing {calculator}...")
            
            result = await self.run_single_test(row, browser)
            self.results.append(result)
            
            # Update stats
            self.stats["total"] += 1
            status = result["status"]
            
            if status == "passed":
                self.stats["passed"] += 1
                print(f"  ✅ PASSED")
            elif status == "failed":
                self.stats["failed"] += 1
                print(f"  ❌ FAILED - Expected: {result.get('ground_truth')}, Got: {result.get('agent_result')}")
            elif status == "error":
                self.stats["errors"] += 1
                print(f"  ⚠️ ERROR - {result.get('error')}")
            else:
                print(f"  ⏭️ SKIPPED - {result.get('reason')}")
            
            # Update per-calculator stats
            if calculator not in self.stats["by_calculator"]:
                self.stats["by_calculator"][calculator] = {"total": 0, "passed": 0, "failed": 0, "errors": 0}
            
            calc_stats = self.stats["by_calculator"][calculator]
            calc_stats["total"] += 1
            if status in calc_stats:
                calc_stats[status] += 1
        
        # Close browser properly
        try:
            if hasattr(browser, 'close'):
                await browser.close()
            elif hasattr(browser, 'context') and hasattr(browser.context, 'close'):
                await browser.context.close()
        except Exception as e:
            print(f"Warning: Could not close browser: {e}")
        
        # Save results
        self._save_results()
        self._print_summary()
    
    def _save_results(self):
        """Save benchmark results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"benchmark_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                "stats": self.stats,
                "results": self.results,
                "timestamp": timestamp
            }, f, indent=2)
        
        print(f"\n📁 Results saved to {results_file}")
    
    def _print_summary(self):
        """Print benchmark summary"""
        print("\n" + "="*60)
        print("📊 BENCHMARK SUMMARY")
        print("="*60)
        
        total = self.stats["total"]
        passed = self.stats["passed"]
        failed = self.stats["failed"]
        errors = self.stats["errors"]
        
        print(f"\nOverall Results:")
        print(f"  Total Tests:  {total}")
        print(f"  ✅ Passed:    {passed} ({passed/total*100:.1f}%)" if total > 0 else "  ✅ Passed: 0")
        print(f"  ❌ Failed:    {failed} ({failed/total*100:.1f}%)" if total > 0 else "  ❌ Failed: 0")
        print(f"  ⚠️ Errors:    {errors} ({errors/total*100:.1f}%)" if total > 0 else "  ⚠️ Errors: 0")
        
        print(f"\nBy Calculator:")
        for calc, stats in self.stats["by_calculator"].items():
            total_calc = stats["total"]
            passed_calc = stats["passed"]
            print(f"  {calc}:")
            print(f"    ✅ {passed_calc}/{total_calc} passed ({passed_calc/total_calc*100:.1f}%)" if total_calc > 0 else f"    No tests")
        
        print("\n" + "="*60)


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run calculator benchmarks')
    parser.add_argument('--input', '-i', required=True, help='Input CSV file path')
    parser.add_argument('--output', '-o', help='Output JSON file name (optional)')
    parser.add_argument('--max-tests', '-m', type=int, help='Maximum number of tests to run')
    parser.add_argument('--chunk-id', '-c', help='Chunk identifier for naming')
    
    args = parser.parse_args()
    
    # Run benchmark
    benchmark = CalculatorBenchmark(args.input, max_tests=args.max_tests)
    
    # Override save file name if provided
    if args.output or args.chunk_id:
        original_save = benchmark._save_results
        
        def custom_save():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if args.output:
                results_file = args.output
            elif args.chunk_id:
                results_file = f"benchmark_results_chunk_{args.chunk_id}_{timestamp}.json"
            else:
                results_file = f"benchmark_results_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump({
                    "stats": benchmark.stats,
                    "results": benchmark.results,
                    "timestamp": timestamp,
                    "chunk_id": args.chunk_id
                }, f, indent=2)
            
            print(f"\n📁 Results saved to {results_file}")
        
        benchmark._save_results = custom_save
    
    await benchmark.run_benchmark()


if __name__ == "__main__":
    asyncio.run(main())

