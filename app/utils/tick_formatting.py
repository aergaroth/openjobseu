def format_tick_summary(payload: dict) -> str:
    metrics = payload.get("metrics", {})
    ingestion = metrics.get("ingestion", {})
    per_source = ingestion.get("per_source", {})

    lines = []
    lines.append(f"Tick finished ({payload.get('mode')})")
    lines.append("=" * 60)
    lines.append("")

    header = (
        f"{'SOURCE':<16}"
        f"{'RAW':>6}"
        f"{'OK':>6}"
        f"{'REJ':>6}"
        f"{'NR':>6}"
        f"{'GEO':>6}"
        f"{'REJ%':>7}"
        f"{'TIME(ms)':>10}"
    )

    lines.append(header)
    lines.append("-" * len(header))

    for name, data in per_source.items():
        policy = data.get("policy", {})
        reasons = policy.get("by_reason", {})

        raw = data.get("raw_count", 0)
        accepted = data.get("persisted_count", 0)
        rejected = policy.get("rejected_total", 0)
        non_remote = reasons.get("non_remote", 0)
        geo_restriction = reasons.get("geo_restriction", 0)
        duration = data.get("duration_ms", 0)

        rej_percent = (rejected / raw * 100) if raw else 0.0

        line = (
            f"{name:<16}"
            f"{raw:>6}"
            f"{accepted:>6}"
            f"{rejected:>6}"
            f"{non_remote:>6}"
            f"{geo_restriction:>6}"
            f"{rej_percent:>7.1f}"
            f"{duration:>10}"
        )

        lines.append(line)

    lines.append("")
    lines.append("TOTALS")

    totals_line = (
        f"raw={ingestion.get('raw_count', 0)}  "
        f"persisted={ingestion.get('persisted_count', 0)}  "
        f"skipped={ingestion.get('skipped_count', 0)}  "
        f"duration={metrics.get('tick_duration_ms', 0)} ms"
    )

    lines.append(totals_line)
    lines.append("")

    return "\n".join(lines)
