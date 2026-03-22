from app.domain.taxonomy.enums import RemoteClass


def _normalize_remote_model_for_metrics(remote_model: str | None) -> str:
    model = (remote_model or "").strip().lower()
    if model == RemoteClass.REMOTE_ONLY.value:
        return RemoteClass.REMOTE_ONLY.value
    if model in {RemoteClass.REMOTE_REGION_LOCKED.value, "remote_but_geo_restricted"}:
        return "remote_but_geo_restricted"
    if model in {"office_first", "hybrid"}:
        return RemoteClass.NON_REMOTE.value
    return RemoteClass.UNKNOWN.value


class IngestionMetrics:
    def __init__(self, fetched_count: int = 0):
        self.fetched = fetched_count
        self.normalized = 0
        self.accepted = 0
        self.skipped = 0
        self.rejected_policy_count = 0
        self.hard_geo_rejected_count = 0
        self.rejected_by_reason = {
            RemoteClass.NON_REMOTE.value: 0,
            "geo_restriction": 0,
        }
        self.remote_model_counts = {
            RemoteClass.REMOTE_ONLY.value: 0,
            "remote_but_geo_restricted": 0,
            RemoteClass.NON_REMOTE.value: 0,
            RemoteClass.UNKNOWN.value: 0,
        }
        self.salary_detected = 0
        self.salary_missing = 0

    def observe_normalized(self):
        self.normalized += 1

    def observe_rejection(self, reason: str | None):
        if reason == "geo_restriction_hard":
            self.rejected_policy_count += 1
            self.rejected_by_reason["geo_restriction"] += 1
            self.hard_geo_rejected_count += 1
        elif reason in self.rejected_by_reason:
            self.rejected_policy_count += 1
            self.rejected_by_reason[reason] += 1

    def observe_skip(self):
        self.skipped += 1

    def observe_accept(self):
        self.accepted += 1

    def observe_remote_model(self, remote_model: str | None):
        metric_remote_model = _normalize_remote_model_for_metrics(remote_model)
        self.remote_model_counts[metric_remote_model] += 1

    def observe_salary(self, has_salary: bool):
        if has_salary:
            self.salary_detected += 1
        else:
            self.salary_missing += 1

    def to_result_dict(self) -> dict:
        return {
            "fetched": self.fetched,
            "normalized_count": self.normalized,
            "accepted": self.accepted,
            "skipped": self.skipped,
            "rejected_policy_count": self.rejected_policy_count,
            "rejected_by_reason": self.rejected_by_reason.copy(),
            "remote_model_counts": self.remote_model_counts.copy(),
            "hard_geo_rejected_count": self.hard_geo_rejected_count,
            "salary_detected": self.salary_detected,
            "salary_missing": self.salary_missing,
        }
