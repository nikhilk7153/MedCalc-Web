"""
Test script to verify browser-use setup with OpenAI
"""
import asyncio
import os
from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_setup():
    """Test basic browser-use functionality"""
    
    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not set")
        print("\nPlease set it:")
        print("  export OPENAI_API_KEY='your-key'")
        print("\nGet your OpenAI API key at: https://platform.openai.com/api-keys")
        return False
    
    print("✅ OPENAI_API_KEY is set")
    print("🧪 Testing browser-use with OpenAI (gpt-4.1-mini)...\n")
    
    try:
        # Simple test task
        llm = ChatOpenAI(model="gpt-4.1-mini")
        browser = Browser(headless=True)
        
        task = "Navigate to http://localhost:8000/centor-score.html and tell me the page title"
        
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_actions_per_step=3
        )
        
        history = await agent.run(max_steps=5)
        
        print(f"✅ Browser-use is working with OpenAI!")
        print(f"   Steps taken: {history.number_of_steps()}")
        print(f"   Result: {history.final_result()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_setup())
    exit(0 if success else 1)

