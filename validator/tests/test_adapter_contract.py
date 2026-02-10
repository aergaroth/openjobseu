import ast
from pathlib import Path


def test_adapters_are_fetch_only_no_normalize_methods():
    repo_root = Path(__file__).resolve().parents[2]
    adapters_dir = repo_root / "ingestion" / "adapters"

    offenders: list[str] = []

    for file_path in sorted(adapters_dir.glob("*.py")):
        if file_path.name == "__init__.py":
            continue

        tree = ast.parse(file_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "normalize":
                    offenders.append(f"{file_path.relative_to(repo_root)}:{node.lineno}")

    assert not offenders, (
        "Adapters must be fetch-only. Move normalization to app/workers/normalization. "
        f"Found normalize() in: {', '.join(offenders)}"
    )
