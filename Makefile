PY ?= python3
PIP ?= pip

.PHONY: help install install-all test lint server docker-build docker-run vscode-build clean dist sample-validate

help:
	@echo "Targets:"
	@echo "  install        - install core package in editable mode"
	@echo "  install-all    - install with all optional extras"
	@echo "  test           - run pytest"
	@echo "  server         - run FastAPI on 127.0.0.1:8765"
	@echo "  docker-build   - build server Docker image"
	@echo "  docker-run     - run server container"
	@echo "  vscode-build   - compile the VS Code extension"
	@echo "  sample-validate- run a small fidelity check on bundled prompts"
	@echo "  dist           - build sdist + wheel"
	@echo "  clean          - remove build artefacts"

install:
	$(PIP) install -e .

install-all:
	$(PIP) install -e ".[tokenizer,server,classifier,validate,dev]"

test:
	PYTHONPATH=. $(PY) -m pytest tests/ -v

server:
	PYTHONPATH=. $(PY) -m uvicorn server.main:app --host 127.0.0.1 --port 8765 --reload

docker-build:
	docker build -t tokensqueeze:0.1.0 -f server/Dockerfile .

docker-run:
	docker run --rm -p 8765:8765 tokensqueeze:0.1.0

vscode-build:
	cd vscode-extension && npm install && npm run compile

sample-validate:
	@printf '{"prompt":"Write a Python function that checks if a number is prime"}\n{"prompt":"Please summarize this article in three sentences"}\n{"prompt":"Could you write a JavaScript function that returns the sum of an array"}\n' > /tmp/_tsq_prompts.jsonl
	PYTHONPATH=. $(PY) -m validate.fidelity --input /tmp/_tsq_prompts.jsonl --strategy auto

dist:
	$(PY) -m pip install --upgrade build
	$(PY) -m build

clean:
	rm -rf build/ dist/ *.egg-info **/__pycache__ .pytest_cache vscode-extension/out
