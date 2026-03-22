from app.domain.taxonomy.enums import RemoteClass


def format_tick_summary(payload: dict) -> str:
    if payload.get("phase") == "trigger_accepted":
        lines = [
            f"Tick accepted ({payload.get('mode')})",
            "=" * 60,
            "",
            f"tick_id={payload.get('tick_id')}",
            f"request_id={payload.get('request_id')}",
            f"group={payload.get('group')}",
            f"scheduler_execution={payload.get('scheduler_execution')}",
            f"task_name={payload.get('task_name')}",
            "",
        ]
        return "\n".join(lines)

    metrics = payload.get("metrics", {})
    ingestion = metrics.get("ingestion", {})
    per_source = ingestion.get("per_source", {})
    if not per_source and ingestion:
        source_name = str(ingestion.get("source") or "employer_ing")
        per_source = {source_name: dict(ingestion)}

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
        f"{'RO':>6}"
        f"{'RG':>6}"
        f"{'UNK':>6}"
        f"{'REJ%':>7}"
        f"{'TIME':>10}"
    )

    lines.append(header)
    lines.append("-" * len(header))

    for name, data in per_source.items():
        policy = data.get("policy", {})
        reasons = (
            policy.get("by_reason") or data.get("policy_rejected_by_reason") or data.get("rejected_by_reason") or {}
        )

        raw = data.get("raw_count", data.get("fetched_count", 0))
        accepted = data.get("persisted_count", data.get("accepted_count", 0))
        rejected = policy.get(
            "rejected_total",
            data.get("policy_rejected_total", data.get("rejected_policy_count", 0)),
        )
        non_remote = reasons.get(RemoteClass.NON_REMOTE.value, 0)
        geo_restriction = reasons.get("geo_restriction", 0)
        remote_model = data.get("remote_model") or data.get("remote_model_counts") or {}
        remote_only = remote_model.get(RemoteClass.REMOTE_ONLY.value, 0)
        remote_geo_restricted = remote_model.get("remote_but_geo_restricted", 0)
        remote_unknown = remote_model.get(RemoteClass.UNKNOWN.value, 0)
        duration = data.get("duration_ms", data.get("ingestion_loop_duration_ms", 0))

        rej_percent = (rejected / raw * 100) if raw else 0.0

        line = (
            f"{name:<16}"
            f"{raw:>6}"
            f"{accepted:>6}"
            f"{rejected:>6}"
            f"{non_remote:>6}"
            f"{geo_restriction:>6}"
            f"{remote_only:>6}"
            f"{remote_geo_restricted:>6}"
            f"{remote_unknown:>6}"
            f"{rej_percent:>7.1f}"
            f"{duration:>10}"
        )

        lines.append(line)

    lines.append("")
    lines.append("TOTALS")

    totals_line = (
        f"raw={ingestion.get('raw_count', ingestion.get('fetched_count', 0))}  "
        f"persisted={ingestion.get('persisted_count', ingestion.get('accepted_count', 0))}  "
        f"skipped={ingestion.get('skipped_count', ingestion.get('skipped', 0))}  "
        f"duration={metrics.get('tick_duration_ms', 0)} ms"
    )

    lines.append(totals_line)
    lines.append("")

    return "\n".join(lines)
