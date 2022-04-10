requirements.txt: setup.py
	@rm -rf .venv
	test -d .venv || python -m venv .venv
	.venv/bin/pip install -e "."
	-@.venv/bin/pip freeze | grep -v "^#" | grep -v "/src" > requirements.txt

requirements-test.txt: requirements.txt
	test -d .venv || python -m venv .venv
	.venv/bin/pip install -e ".[test]"
	-@.venv/bin/pip freeze | grep -v "^#" | grep -v "/src" > requirements-test.txt

requirements-dev.txt: requirements-test.txt
	test -d .venv || python -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	-@.venv/bin/pip freeze | grep -v "^#" | grep -v "/src" > requirements-dev.txt

.venv/bin/activate: requirements-dev.txt
	test -d .venv || python -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

.coverage: $(SOURCES) $(TESTS)
	.venv/bin/pytest --cov=plutus test/

.PHONY: help
help: ## Show Makefile targets and descriptions
	@echo 'Usage: make [target] ...'
	@echo
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

.PHONY: reqs
reqs: requirements-dev.txt ## Create version-pinned requiements files

.PHONY: venv
venv: .venv/bin/activate ## Create Python virtual env and install dependencies
	@echo "Activate Python virtual env with:"
	@echo "    source .venv/bin/activate"

.PHONY: lint
lint: ## Run code linting
	.venv/bin/prospector src/
	.venv/bin/flake8 src/
	.venv/bin/mypy src/

.PHONY: test
test: lint .coverage ## Run tests and code linting

.PHONY: clean
clean: ## Cleanup build and dev artifacts
	-find . -type d -name __pycache__ -exec rm -r {} \;
	-find . -type d -name .mypy_cache -exec rm -r {} \;
	rm -f .coverage
	rm -rf .venv/
