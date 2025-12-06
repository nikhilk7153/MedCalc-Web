"""
Test script for Omni Calculator - follows same pattern as run_simple_benchmark.py
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Omni Calculator URL
OMNI_CALCULATOR_URL = "https://www.omnicalculator.com/health/corrected-calcium"

# Create output directories
SCREENSHOT_DIR = Path("omni_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)
LOGS_DIR = Path("omni_logs")
LOGS_DIR.mkdir(exist_ok=True)


async def main():
    """Run Omni Calculator tests - same pattern as run_simple_benchmark.py"""
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY='your-key'\n")
        return
    
    print("="*70)
    print("  Omni Calculator Test Runner")
    print("  Testing: Corrected Calcium Calculator")
    print("="*70)
    print()
    
    # Test cases
    test_cases = [
        {
            "name": "Test Case 1",
            "calcium": 8.4,
            "calcium_unit": "mg/dL",
            "albumin": 2.8,
            "albumin_unit": "g/dL",
            "expected": 9.36
        },
        {
            "name": "Test Case 2",
            "calcium": 10.3,
            "calcium_unit": "mg/dL",
            "albumin": 2.9,
            "albumin_unit": "g/dL",
            "expected": 11.18
        },
        {
            "name": "Test Case 3",
            "calcium": 8.1,
            "calcium_unit": "mg/dL",
            "albumin": 3.3,
            "albumin_unit": "g/dL",
            "expected": 8.66
        }
    ]
    
    # Initialize stats
    stats = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0
    }
    results = []
    
    # Create LLM instance (reused)
    llm = ChatOpenAI(model="gpt-5-nano")
    
    # Create timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"omni_calculator_results_{timestamp}.json"
    
    # Run each test
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] {test_case['name']}")
        print(f"  Calcium: {test_case['calcium']} {test_case['calcium_unit']}")
        print(f"  Albumin: {test_case['albumin']} {test_case['albumin_unit']}")
        print(f"  Expected: {test_case['expected']} mg/dL")
        
        # Create task
        task = f"""You are a medical AI assistant testing a web calculator.

TASK:
1. Navigate to {OMNI_CALCULATOR_URL}
2. Find the calculator form on the page (you may need to scroll)
3. Enter {test_case['calcium']} in the Serum calcium field
4. Enter {test_case['albumin']} in the Albumin field
5. Make sure units are mg/dL for calcium and g/dL for albumin
6. Read the Corrected calcium result from the calculator
7. Return ONLY this JSON: {{"answer": <number>}}

CRITICAL: Use the calculator on the webpage, do NOT calculate yourself.
Example response: {{"answer": 9.36}}"""

        # Create fresh browser for this test
        print(f"  🌐 Starting fresh browser...")
        browser = Browser(
            headless=False,
            window_size={'width': 1920, 'height': 1080}
        )
        
        # Create file paths for this test
        safe_name = test_case['name'].replace(' ', '_')
        log_path = LOGS_DIR / f"{i:03d}_{safe_name}_{timestamp}.log"
        
        # Set up logging to file for this test
        file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
        
        try:
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                max_actions_per_step=10,
                use_vision=True,
                use_thinking=False,
                llm_timeout=120
            )
            
            history = await agent.run(max_steps=30)
            result = history.final_result()
            
            print(f"  📝 Agent response: {str(result)[:100]}")
            
            # Parse JSON response from agent
            agent_answer = None
            final_json = None
            
            try:
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
                truth_num = float(test_case['expected'])
                
                if agent_num is None:
                    print(f"  ❌ FAILED - No answer extracted from: {str(result)[:50]}")
                    stats["failed"] += 1
                    results.append({
                        "test": test_case['name'],
                        "status": "failed",
                        "expected": truth_num,
                        "result": str(result),
                        "agent_json": final_json
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
                        "test": test_case['name'],
                        "status": "passed" if is_correct else "failed",
                        "expected": truth_num,
                        "result": agent_num,
                        "agent_json": final_json,
                        "raw_response": str(result)
                    })
                
            except (ValueError, TypeError) as e:
                print(f"  ❌ FAILED - Could not parse result: {result}")
                stats["failed"] += 1
                results.append({
                    "test": test_case['name'],
                    "status": "failed",
                    "expected": test_case['expected'],
                    "result": str(result),
                    "agent_json": final_json
                })
            
            stats["total"] += 1
            
        except Exception as e:
            print(f"  ⚠️ ERROR - {str(e)[:100]}")
            stats["errors"] += 1
            stats["total"] += 1
            results.append({
                "test": test_case['name'],
                "status": "error",
                "error": str(e)
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
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    total = stats["total"]
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed:   {stats['passed']} ({stats['passed']/total*100:.1f}%)" if total > 0 else "✅ Passed: 0")
    print(f"❌ Failed:   {stats['failed']} ({stats['failed']/total*100:.1f}%)" if total > 0 else "❌ Failed: 0")
    print(f"⚠️ Errors:   {stats['errors']} ({stats['errors']/total*100:.1f}%)" if total > 0 else "⚠️ Errors: 0")
    
    print(f"\n📁 Results saved to: {results_file}")
    print(f"📋 Logs saved to: {LOGS_DIR}/")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
