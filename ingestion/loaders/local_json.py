import json
from pathlib import Path


def load_local_jobs(path: str) -> list[dict]:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Job source not found: {path}")

    with file_path.open() as f:
        return json.load(f)
