VIRTUAL_ENV ?= .venv

all: $(VIRTUAL_ENV)

.PHONY: help
# target: help - Display callable targets
help:
	@egrep "^# target:" [Mm]akefile

.PHONY: clean
# target: clean - Display callable targets
clean:
	rm -rf build/ dist/ docs/_build *.egg-info
	find $(CURDIR) -name "*.py[co]" -delete
	find $(CURDIR) -name "*.orig" -delete
	find $(CURDIR)/$(MODULE) -name "__pycache__" | xargs rm -rf

# ==============
#  Bump version
# ==============

.PHONY: release
VERSION?=minor
# target: release - Bump version
release:
	@git checkout master
	@git pull
	@git checkout develop
	@git pull
	@$(VIRTUAL_ENV)/bin/pip install bump2version
	@$(VIRTUAL_ENV)/bin/bump2version $(VERSION)
	@git checkout master
	@git merge develop
	@git checkout develop
	@git push origin develop master
	@git push --tags

.PHONY: minor
minor: release

.PHONY: patch
patch:
	make release VERSION=patch

.PHONY: major
major:
	make release VERSION=major

# =============
#  Development
# =============

$(VIRTUAL_ENV): pyproject.toml
	@[ -d $(VIRTUAL_ENV) ] || python -m venv $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/pip install .[tests,dev,example]
	@$(VIRTUAL_ENV)/bin/pre-commit install --hook-type pre-push
	@touch $(VIRTUAL_ENV)

.PHONY: run
# target: run - Run example
run: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/uvicorn --port 5000 --reload example:app

.PHONY: test t
# target: test - Run tests
test t: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/pytest tests.py

.PHONY: mypy
# target: mypy - Check types
mypy: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/mypy muffin_babel

.PHONY: example
# target: example - Run an example
example: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/uvicorn --port 5000 --reload example:app
