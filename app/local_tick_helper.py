def format_tick_summary(payload: dict) -> str:
    metrics = payload.get("metrics", {})
    ingestion = metrics.get("ingestion", {})
    per_source = ingestion.get("per_source", {})

    lines = []
    lines.append(f"Tick finished ({payload.get('mode')})")
    lines.append("-" * 40)

    lines.append("Per source:")
    for name, data in per_source.items():
        lines.append(
            f"- {name:<16} raw={data.get('raw_count')} "
            f"accepted={data.get('persisted_count')} "
            f"rejected={data.get('policy', {}).get('rejected_total')} "
            f"({data.get('duration_ms')} ms)"
        )

    totals = ingestion
    lines.append("")
    lines.append("Totals:")
    lines.append(f"raw={totals.get('raw_count')}")
    lines.append(f"persisted={totals.get('persisted_count')}")
    lines.append(f"skipped={totals.get('skipped_count')}")
    lines.append(f"duration={metrics.get('tick_duration_ms')} ms")

    return "\n".join(lines)
