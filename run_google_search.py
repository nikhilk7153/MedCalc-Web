import asyncio

from browser_use import Agent, Browser, ChatOpenAI


async def main() -> None:
	browser = Browser()
	agent = Agent(
		task="Go to google.com, search for 'MedCalc clinical calculator suite', read the first result, and report the page title.",
		llm=ChatOpenAI(model='gpt-4.1-mini'),
		browser=browser,
		use_vision=True,
	)
	await agent.run()


if __name__ == '__main__':
	asyncio.run(main())


