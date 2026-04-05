"""
Filter a `pg_restore -l` list file to exclude legacy objects that are not
needed by this application during a Neon -> Aiven migration.

By default, the script removes entries related to:
- EXTENSION/COMMENT `pg_session_jwt`
- schema/function objects under `pgrst`
"""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_PATTERNS = (
    "EXTENSION - pg_session_jwt",
    "COMMENT - EXTENSION pg_session_jwt",
    "SCHEMA - pgrst",
    " pgrst.",
    "FUNCTION - pgrst.",
    " pgrst ",
)


def should_exclude(line: str, patterns: tuple[str, ...] = DEFAULT_PATTERNS) -> bool:
    normalized = line.strip()
    if not normalized or normalized.startswith(";"):
        return False
    return any(pattern in normalized for pattern in patterns)


def filter_restore_list(content: str, patterns: tuple[str, ...] = DEFAULT_PATTERNS) -> tuple[str, int]:
    kept_lines: list[str] = []
    removed = 0

    for line in content.splitlines(keepends=True):
        if should_exclude(line, patterns=patterns):
            removed += 1
            continue
        kept_lines.append(line)

    return "".join(kept_lines), removed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Filter pg_restore list files to skip legacy pg_session_jwt / pgrst objects."
    )
    parser.add_argument("input", help="Path to the input file produced by `pg_restore -l`.")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the filtered output file. Defaults to <input>.filtered.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(f"{input_path.suffix}.filtered")

    content = input_path.read_text(encoding="utf-8")
    filtered_content, removed = filter_restore_list(content)
    output_path.write_text(filtered_content, encoding="utf-8")

    print(f"Filtered restore list written to: {output_path}")
    print(f"Removed entries: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
