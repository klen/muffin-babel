VIRTUAL_ENV ?= .venv

# =============
#  Development
# =============

$(VIRTUAL_ENV): uv.lock .pre-commit-config.yaml
	@uv sync
	@uv run pre-commit install
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

# ==============
#  Bump version
# ==============

VERSION?=minor

# target: release - Bump version
.PHONY: release
release:
	@git checkout develop
	@git pull
	@git checkout master
	@git merge develop
	@git pull
	@uvx bump-my-version bump $(VERSION)
	@uv lock
	@git commit -am "build(release): `uv version --short`"
	@git tag `uv version --short`
	@git checkout develop
	@git merge master
	@git push --tags origin develop master

.PHONY: minor
minor: release

.PHONY: patch
patch:
	@make release VERSION=patch

.PHONY: major
major:
	@make release VERSION=major

v:
	@echo `uv version --short`
