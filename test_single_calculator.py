"""
Test a single calculator to verify browser-use setup
"""
import asyncio
import os
from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_single_calculator():
    """Test one calculator end-to-end"""
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not set")
        print("Please run: export OPENAI_API_KEY='your-key'")
        return
    
    print("✅ API Key found")
    print("🧪 Testing MELD-Na calculator...\n")
    
    try:
        llm = ChatOpenAI(model="gpt-5-mini")
        browser = Browser(
            headless=False,  # Show browser for debugging
            window_size={'width': 1400, 'height': 1000}
        )
        
        task = """Navigate to http://localhost:8000/meld-na.html

Fill out the calculator with these values:
- Serum creatinine: 1.3 mg/dL
- Total bilirubin: 2.4 mg/dL
- Sodium: 133 mEq/L
- INR: 1.2

Then click the "Calculate MELD-Na" button and extract the numeric score.
Return ONLY the final numerical score without units."""
        
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_actions_per_step=5
        )
        
        print("🤖 Agent is running...\n")
        history = await agent.run(max_steps=20)
        
        print(f"\n✅ Test completed!")
        print(f"   Steps taken: {history.number_of_steps()}")
        print(f"   Final result: {history.final_result()}")
        print(f"   Success: {history.is_done()}")
        
        if history.has_errors():
            print(f"\n⚠️ Errors encountered:")
            for error in history.errors():
                if error:
                    print(f"   - {error}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_calculator())

