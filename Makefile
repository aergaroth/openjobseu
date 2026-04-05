.PHONY: compile sync deps lint check

# Reguły plikowe: uruchamiają pip-compile TYLKO gdy plik .in jest nowszy od .txt
requirements.txt: requirements.in
	uv pip compile requirements.in -o requirements.txt

requirements-dev.txt: requirements-dev.in
	uv pip compile requirements-dev.in -o requirements-dev.txt

# Kompiluje oba pliki .in do postaci .txt (odpala się tylko przy rzeczywistych zmianach)
compile: requirements.txt requirements-dev.txt

# Synchronizuje wirtualne środowisko z wygenerowanymi plikami .txt
sync:
	uv pip sync requirements.txt requirements-dev.txt

# Wykonuje kompilację, a następnie od razu synchronizuje środowisko
deps: compile sync

# Uruchamia linter i formatter Ruff (poprzez pre-commit) na wszystkich plikach
lint:
	pre-commit run ruff --all-files
	pre-commit run ruff-format --all-files

# Uruchamia WSZYSTKIE zdefiniowane hooki (w tym customowe sprawdzarki np. check-no-prints)
check: compile
	@if .venv/bin/python scripts/pytest_precommit_guard.py; then \
		pre-commit run --all-files; \
	else \
		echo "WARNING: local test database is unavailable; skipping pytest hook in pre-commit."; \
		SKIP=pytest pre-commit run --all-files; \
	fi
