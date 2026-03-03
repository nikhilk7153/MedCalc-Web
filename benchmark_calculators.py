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

from benchmark_evaluation import evaluate_prediction, parse_agent_result

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
            "skipped": 0,
            "by_calculator": {},
            "by_category": {},
            "by_output_type": {},
        }
    
    async def run_single_test(self, row: dict, browser: Browser) -> dict:
        """Run a single calculator test"""
        calculator_name = row["Calculator Name"]
        calculator_id = row.get("Calculator ID", "")
        row_number = row.get("Row Number")
        category = row.get("Category", "unknown")
        output_type = row.get("Output Type", "unknown")
        html_file = CALCULATOR_MAPPING.get(calculator_name)
        
        if not html_file:
            return {
                "site": "local",
                "row_number": row_number,
                "calculator_id": calculator_id,
                "status": "skipped",
                "failure_type": "coverage_missing_target",
                "reason": f"No HTML mapping for {calculator_name}",
                "calculator": calculator_name,
                "category": category,
                "output_type": output_type,
            }
        
        # Parse relevant entities (inputs)
        try:
            entities = eval(row["Relevant Entities"])  # Safe in this context
        except Exception as e:
            return {
                "site": "local",
                "row_number": row_number,
                "calculator_id": calculator_id,
                "status": "error",
                "failure_type": "input_extraction_error",
                "reason": f"Failed to parse entities: {str(e)}",
                "calculator": calculator_name,
                "category": category,
                "output_type": output_type,
            }
        
        url = f"{BASE_URL}/{html_file}"
        ground_truth = row["Ground Truth Answer"]
        lower_limit = row.get("Lower Limit")
        upper_limit = row.get("Upper Limit")
        
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
            
            result = history.final_result()
            # Reuse the same evaluator as external-site runners to keep
            # comparisons apples-to-apples across benchmark modes.
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
            is_correct = scoring["is_correct"]

            return {
                "site": "local",
                "row_number": row_number,
                "calculator_id": calculator_id,
                "status": "passed" if is_correct else "failed",
                "failure_type": scoring["failure_type"],
                "scoring_rule": scoring["scoring_rule"],
                "calculator": calculator_name,
                "category": category,
                "output_type": output_type,
                "url": url,
                "ground_truth": scoring["normalized_truth"],
                "result": scoring["normalized_prediction"],
                "raw_ground_truth": ground_truth,
                "raw_lower_limit": lower_limit,
                "raw_upper_limit": upper_limit,
                "lower_bound": scoring["lower_bound"],
                "upper_bound": scoring["upper_bound"],
                "agent_answer": parsed["agent_answer"],
                "agent_json": parsed["agent_json"],
                "raw_response": parsed["raw_response"],
                "extraction_method": parsed["extraction_method"],
                "is_correct": is_correct,
                "timing": {
                    "wall_seconds": history.total_duration_seconds(),
                    "agent_steps": history.number_of_steps(),
                    "llm_calls": None,
                    "total_tokens": None,
                },
            }
            
        except Exception as e:
            return {
                "site": "local",
                "row_number": row_number,
                "calculator_id": calculator_id,
                "status": "error",
                "failure_type": "runtime_exception",
                "calculator": calculator_name,
                "category": category,
                "output_type": output_type,
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
            status = result["status"]
            calculator = result.get("calculator", calculator)
            category = result.get("category", "unknown")
            output_type = result.get("output_type", "unknown")
            
            _update_bucket(self.stats["by_calculator"], calculator, status)
            _update_bucket(self.stats["by_category"], category, status)
            _update_bucket(self.stats["by_output_type"], output_type, status)
            
            if status == "passed":
                self.stats["total"] += 1
                self.stats["passed"] += 1
                print(f"  ✅ PASSED")
            elif status == "failed":
                self.stats["total"] += 1
                self.stats["failed"] += 1
                print(f"  ❌ FAILED - Expected: {result.get('ground_truth')}, Got: {result.get('result')} ({result.get('failure_type')})")
            elif status == "error":
                self.stats["total"] += 1
                self.stats["errors"] += 1
                print(f"  ⚠️ ERROR - {result.get('error')}")
            else:
                self.stats["skipped"] += 1
                print(f"  ⏭️ SKIPPED - {result.get('reason')}")
        
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
                "metrics_by_category": _metrics_view(self.stats["by_category"]),
                "metrics_by_output_type": _metrics_view(self.stats["by_output_type"]),
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
        skipped = self.stats["skipped"]
        
        print(f"\nOverall Results:")
        print(f"  Total Tests:  {total}")
        print(f"  ✅ Passed:    {passed} ({passed/total*100:.1f}%)" if total > 0 else "  ✅ Passed: 0")
        print(f"  ❌ Failed:    {failed} ({failed/total*100:.1f}%)" if total > 0 else "  ❌ Failed: 0")
        print(f"  ⚠️ Errors:    {errors} ({errors/total*100:.1f}%)" if total > 0 else "  ⚠️ Errors: 0")
        print(f"  ⏭️ Skipped:   {skipped}")
        
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
                    "metrics_by_category": _metrics_view(benchmark.stats["by_category"]),
                    "metrics_by_output_type": _metrics_view(benchmark.stats["by_output_type"]),
                    "results": benchmark.results,
                    "timestamp": timestamp,
                    "chunk_id": args.chunk_id
                }, f, indent=2)
            
            print(f"\n📁 Results saved to {results_file}")
        
        benchmark._save_results = custom_save
    
    await benchmark.run_benchmark()


if __name__ == "__main__":
    asyncio.run(main())
