# Directories for the virtualenvs
VENV1 := .pp

# Setup virtual environments
.PHONY: setup
setup:
	python3.12 -m venv --clear $(VENV1)

.PHONY: deps
deps:
	$(VENV1)/bin/python -m pip install -r requirements-dev.txt

.PHONY: publish
publish: setup deps test
	./scripts/publish.sh

.PHONY: test
test: setup deps
	$(VENV1)/bin/pytest
