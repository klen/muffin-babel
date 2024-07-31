VIRTUAL_ENV ?= .venv

# =============
#  Development
# =============

$(VIRTUAL_ENV): poetry.lock .pre-commit-config.yaml
	@[ -d $(VIRTUAL_ENV) ] || python -m venv $(VIRTUAL_ENV)
	@poetry install --with dev
	@poetry run pre-commit install
	@poetry self add poetry-bumpversion
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

.PHONY: release
VERSION?=minor
# target: release - Bump version
release:
	git checkout develop
	git pull
	git checkout master
	git merge develop
	git pull
	@poetry version $(VERSION)
	git commit -am "build(release): `poetry version -s`"
	git tag `poetry version -s`
	git checkout develop
	git merge master
	git push --tags origin develop master

.PHONY: minor
minor: release

.PHONY: patch
patch:
	make release VERSION=patch

.PHONY: major
major:
	make release VERSION=major
