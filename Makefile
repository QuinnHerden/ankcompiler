.PHONY: install format secure test coverage release check

install:
	uv sync

format:
	uv run black --check .

secure:
	uv run bandit -r app -ll

test:
	uv run pytest

coverage:
	uv run pytest --cov=app --cov-report=term-missing --cov-report=json

release:
	bash scripts/check_release.sh

check: release format secure test
