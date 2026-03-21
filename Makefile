MAKEFLAGS=--no-print-directory

# structure
MAIN := 
ARGS ?= 

VENV := .venv
VENV_STATE_PROD := $(VENV)/.install
VENV_STATE_DEV := $(VENV)/.install-dev

UV_LOCK := uv.lock
PYPROJECT_TOML := pyproject.toml

# cache
CACHE_DIRS := __pycache__ .mypy_cache .pytest_cache
CACHE_EXCLUDE = -name "$(VENV)" -prune -o
CACHE_SEARCH = $(foreach cache,$(CACHE_DIRS),-name "$(cache)" -o)
FIND_CACHES = find . \
	$(CACHE_EXCLUDE) \
	-type d \( $(CACHE_SEARCH) -false \) -print

# tools
UV := uv
PYTHON := $(VENV)/bin/python3
FLAKE8 := $(PYTHON) -m flake8 --exclude $(VENV),libs,.git,llm_sdk
MYPY := $(PYTHON) -m mypy --exclude $(VENV) --exclude libs --exclude .git --exclude llm_sdk

# rules
.PHONY: install
install: $(UV_LOCK) $(VENV_STATE_PROD)

.PHONY: install-dev
install-dev: $(UV_LOCK) $(VENV_STATE_DEV)

.PHONY: run
run: install
	@echo "$(UV) run python -m src $(ARGS)"
	@$(UV) run python -m src $(ARGS)

$(VENV_STATE_PROD): $(UV_LOCK) $(PYPROJECT_TOML)
	@$(UV) lock
	@$(UV) sync --no-dev --inexact
	@touch $(UV_LOCK)
	@touch $(VENV_STATE_PROD)

$(VENV_STATE_DEV): $(UV_LOCK) $(PYPROJECT_TOML)
	@$(UV) lock
	@$(UV) sync
	@touch $(UV_LOCK)
	@touch $(VENV_STATE_PROD) $(VENV_STATE_DEV)

.PHONY: cache-clean
cache-clean:
	$(FIND_CACHES) -exec rm -rf {} + 1>/dev/null

.PHONY: clean
clean: cache-clean
	rm -rf $(VENV)

.PHONY: debug
debug: install-dev
	$(PYTHON) -m pdb $(MAIN) $(ARGS)

.PHONY: lint
lint: install-dev
	@$(FLAKE8)
	@$(MYPY) . --check-untyped-defs \
	--warn-unused-ignores --ignore-missing-imports \
	--warn-return-any --disallow-untyped-defs

.PHONY: lint-strict
lint-strict: install-dev
	@$(FLAKE8)
	@$(MYPY) . --strict
