.PHONY: compile sync deps lint check

# Kompiluje oba pliki .in do postaci .txt
compile:
	pip-compile requirements.in
	pip-compile requirements-dev.in

# Synchronizuje wirtualne środowisko z wygenerowanymi plikami .txt
sync:
	pip-sync requirements.txt requirements-dev.txt

# Wykonuje kompilację, a następnie od razu synchronizuje środowisko
deps: compile sync

# Uruchamia linter i formatter Ruff (poprzez pre-commit) na wszystkich plikach
lint:
	pre-commit run ruff --all-files
	pre-commit run ruff-format --all-files

# Uruchamia WSZYSTKIE zdefiniowane hooki (w tym customowe sprawdzarki np. check-no-prints)
check:
	pre-commit run --all-files