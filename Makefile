.PHONY: install test lint format clean build publish web docker compose

install:
	pip install -e ".[dev,langchain,openai,mcp]"

test:
	pytest tests/ -v --tb=short

lint:
	ruff check jep/ tests/
	black --check jep/ tests/

format:
	black jep/ tests/
	ruff check --fix jep/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build:
	python -m build

publish:
	python -m twine upload dist/*

web:
	jep web --port 8080 --reload

docker:
	docker build -t jep-agent-sdk:latest -f docker/Dockerfile .

compose:
	docker-compose up --build
