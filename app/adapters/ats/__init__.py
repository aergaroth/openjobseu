from importlib import import_module
from pathlib import Path


for file in Path(__file__).parent.glob("*.py"):
    if file.stem not in {"__init__", "base", "registry"}:
        import_module(f"{__name__}.{file.stem}")
