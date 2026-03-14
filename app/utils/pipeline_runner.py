import time
import logging
from typing import Callable, Any


def run_pipeline_steps(
    pipeline_name: str,
    steps: list[tuple[str, Callable[[], Any]]],
    logger: logging.Logger,
) -> dict:
    """
    Generic pipeline runner that iterates through steps, records metrics,
    handles errors gracefully, and measures execution time.
    """
    start_time = time.perf_counter()

    metrics = {
        "status": "ok",
        "pipeline": pipeline_name,
    }

    for step_name, step_func in steps:
        try:
            result = step_func()
            metrics[step_name] = result if result is not None else {"status": "ok"}
        except Exception as e:
            logger.exception(
                f"{pipeline_name} pipeline step failed",
                extra={"step": step_name, "pipeline": pipeline_name},
            )
            metrics[step_name] = {"status": "error", "error": str(e)}
            metrics["status"] = "error"

    metrics["duration_ms"] = int((time.perf_counter() - start_time) * 1000)
    return metrics