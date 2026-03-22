.PHONY: compile sync deps lint check

# Reguły plikowe: uruchamiają pip-compile TYLKO gdy plik .in jest nowszy od .txt
requirements.txt: requirements.in
	pip-compile requirements.in

requirements-dev.txt: requirements-dev.in
	pip-compile requirements-dev.in

# Kompiluje oba pliki .in do postaci .txt (odpala się tylko przy rzeczywistych zmianach)
compile: requirements.txt requirements-dev.txt

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
check: compile
	pre-commit run --all-files