from app.domain.compliance.resolver import _resolve_score_and_status


def score(remote_class: str | None, geo_class: str | None) -> int:
    score_value, _ = _resolve_score_and_status(remote_class, geo_class)
    return score_value


def calculate_compliance_score(remote_class: str | None, geo_class: str | None) -> int:
    return score(remote_class, geo_class)
