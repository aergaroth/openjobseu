import ast
from pathlib import Path


def test_ats_adapters_expose_fetch_and_normalize_methods():
    repo_root = Path(__file__).resolve().parents[2]
    adapters_dir = repo_root / "app" / "ats"

    missing_methods: list[str] = []

    for file_path in sorted(adapters_dir.glob("*.py")):
        if file_path.name in {"__init__.py", "base.py", "registry.py"}:
            continue

        tree = ast.parse(file_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            method_names = {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            if "fetch" not in method_names or "normalize" not in method_names:
                missing_methods.append(
                    f"{file_path.relative_to(repo_root)}:{node.lineno}"
                )

    assert not missing_methods, (
        "ATS adapters must implement both fetch() and normalize(). "
        f"Missing in: {', '.join(missing_methods)}"
    )
