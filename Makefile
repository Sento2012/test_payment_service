.PHONY: install lint format type imports test check

install:  ## поставить зависимости (вкл. dev-инструменты)
	pip install -r requirements-dev.txt

lint:  ## статический линт (ruff)
	ruff check src tests

format:  ## автоформат + авто-фиксы (ruff)
	ruff format src tests
	ruff check --fix src tests

type:  ## статическая типизация (mypy)
	mypy

imports:  ## контроль архитектурных границ (import-linter)
	PYTHONPATH=src lint-imports

test:  ## тесты (pytest, integration на testcontainers)
	TESTCONTAINERS_RYUK_DISABLED=true PYTHONPATH=src pytest

check: lint type imports test  ## весь quality gate
