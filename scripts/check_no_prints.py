#!/usr/bin/env python3
import sys
import re


def main():
    # Szukamy słowa 'print' z otwierającym nawiasem
    forbidden_pattern = re.compile(r"\bprint\s*\(")
    errors_found = False

    # sys.argv[1:] zawiera listę plików zmodyfikowanych w tym commicie
    for filepath in sys.argv[1:]:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if forbidden_pattern.search(line):
                    print(f"❌ {filepath}:{line_num}: Znaleziono instrukcję 'print()'. Użyj 'logger'!")
                    errors_found = True

    if errors_found:
        # Wyjście z kodem błędu przerywa operację git commit
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
