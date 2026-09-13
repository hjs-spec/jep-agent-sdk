.PHONY: install test lint format clean build publish web docker compose

install:
	pip install -e ".[dev,langchain,openai]"

test:
	pytest tests/ -v --tb=short

lint:
	ruff check jep_agent/ tests/
	black --check jep_agent/ tests/

format:
	black jep_agent/ tests/
	ruff check --fix jep_agent/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build:
	python -m build

publish:
	python -m twine upload dist/*

web:
	jep-agent web --port 8080 --reload

docker:
	docker build -t jep-agent-sdk:latest -f docker/Dockerfile .

compose:
	docker-compose up --build
