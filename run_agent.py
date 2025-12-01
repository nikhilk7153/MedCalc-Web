import argparse
import asyncio
import csv
import json
import os
import re
from pathlib import Path
from typing import Any

from browser_use import Agent, Browser, ChatOpenAI
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent
HTML_MAP_FILE = PROJECT_ROOT / 'html_to_calculator_ids.json'
RESULTS_DIR = PROJECT_ROOT / 'agent_results'
DEFAULT_BASE_URL = os.getenv('MEDCALC_BASE_URL', 'http://127.0.0.1:8000')
ANSWER_NUMBER_REGEX = re.compile(r'-?\d+(?:\.\d+)?')


class FinalAnswer(BaseModel):
	answer: float


def load_id_to_html() -> dict[int, list[str]]:
	mapping: dict[int, list[str]] = {}
	html_map: dict[str, list[int]] = json.loads(HTML_MAP_FILE.read_text())
	for html_page, ids in html_map.items():
		for calculator_id in ids:
			mapping.setdefault(calculator_id, []).append(html_page)
	return mapping


def load_rows(data_file: Path) -> list[dict[str, str]]:
	with data_file.open(newline='') as csv_file:
		reader = csv.DictReader(csv_file)
		return list(reader)


def ensure_results_dir() -> None:
	RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def extract_numeric_value(text: str) -> float | None:
	if not text:
		return None
	match = ANSWER_NUMBER_REGEX.search(text.replace(',', ''))
	if not match:
		return None
	return float(match.group())


def save_answer(row_number: int, answer_value: float) -> None:
	ensure_results_dir()
	payload = {'answer': answer_value}
	output_file = RESULTS_DIR / f'row_{row_number:04d}.json'
	output_file.write_text(json.dumps(payload, ensure_ascii=False))


def build_task(url: str, row: dict[str, str]) -> str:
	calculator_name = row.get('Calculator Name', 'the specified calculator')
	question = row.get('Question', '').strip()
	patient_note = row.get('Patient Note', '').strip()
	note_section = f'\n\nPatient Note:\n{patient_note}' if patient_note else ''
	question_section = f'\n\nQuestion:\n{question}' if question else ''
	return (
		f'Go to {url} and fill out the "{calculator_name}" form using the patient note values.'
		f'{question_section}{note_section}\n\n'
		'When you finish, respond with JSON exactly in the format {"answer": <numeric_value>} with no units or additional text.'
	)


async def run_case(row_number: int, row: dict[str, str], html_page: str, llm: ChatOpenAI) -> None:
	url = f"{DEFAULT_BASE_URL.rstrip('/')}/{html_page}"
	task = build_task(url, row)
	initial_actions = [{'navigate': {'url': url, 'new_tab': False}}]

	# Each agent gets its own isolated browser instance
	browser = Browser()
	agent = Agent(
		task=task,
		initial_actions=initial_actions,
		llm=llm,
		browser=browser,
		use_vision=True,
		output_model_schema=FinalAnswer,
	)

	print(f'▶️  Row {row_number}: starting {row.get("Calculator Name")} ({url})')
	history = await agent.run()
	answer_value: float | None = None
	if history.structured_output:
		answer_value = float(history.structured_output.answer)
	else:
		final_text = history.final_result()
		answer_value = extract_numeric_value(final_text if isinstance(final_text, str) else str(final_text))

	if answer_value is not None:
		save_answer(row_number, answer_value)
		print(f'✅ Row {row_number}: completed ({history.number_of_steps()} steps) -> {answer_value}')
	else:
		print(f'⚠️  Row {row_number}: completed but no numeric answer could be parsed')


async def process_rows(limit: int | None, start_row: int, concurrency: int, data_file: Path) -> None:
	id_to_html = load_id_to_html()
	rows = load_rows(data_file)
	ensure_results_dir()
	llm = ChatOpenAI(model='gpt-5-mini')

	# Build list of tasks to run
	tasks_to_run = []
	for index, row in enumerate(rows, start=1):
		if index < start_row:
			continue

		if limit is not None and len(tasks_to_run) >= limit:
			break

		calculator_id = int(row['Calculator ID'])
		html_pages = id_to_html.get(calculator_id)
		if not html_pages:
			print(f'⚠️  Row {index}: no HTML mapping for Calculator ID {calculator_id}')
			continue

		tasks_to_run.append((index, row, html_pages[0]))

	print(f'Running {len(tasks_to_run)} cases with concurrency={concurrency}')

	# Process in batches with limited concurrency
	for i in range(0, len(tasks_to_run), concurrency):
		batch = tasks_to_run[i:i+concurrency]
		batch_ids = [idx for idx, _, _ in batch]
		print(f'\n🚀 Starting batch: rows {batch_ids}')
		
		tasks = [run_case(idx, row, html, llm) for idx, row, html in batch]
		results = await asyncio.gather(*tasks, return_exceptions=True)
		
		for (idx, _, _), result in zip(batch, results):
			if isinstance(result, Exception):
				print(f'❌ Row {idx}: failed with error {result}')


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description='Run Browser Use agents for every row in test_data.csv.'
	)
	parser.add_argument(
		'--limit',
		type=int,
		default=None,
		help='Optional max number of rows to process (default: all)',
	)
	parser.add_argument(
		'--start-row',
		type=int,
		default=1,
		help='Row number (1-indexed) to start processing from (default: 1)',
	)
	parser.add_argument(
		'--concurrency',
		type=int,
		default=5,
		help='Number of agents to run in parallel (default: 5)',
	)
	parser.add_argument(
		'--data-file',
		type=str,
		default='test_data.csv',
		help='CSV file to process (default: test_data.csv)',
	)
	return parser.parse_args()


if __name__ == '__main__':
	arguments = parse_args()
	data_file_path = PROJECT_ROOT / arguments.data_file
	asyncio.run(process_rows(
		limit=arguments.limit,
		start_row=arguments.start_row,
		concurrency=arguments.concurrency,
		data_file=data_file_path
	))
