import os
import sys
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from collections import Counter
from sqlalchemy import text

from storage.db_engine import get_engine
from app.domain.compliance.classifiers.geo import classify_geo
from app.domain.compliance.classifiers.remote import classify_remote_model


def shadow_resolve(remote_model: str, geo_classification: str) -> tuple[str, int]:
    # uproszczony model testowy
    if remote_model == "non_remote":
        return "rejected", 0

    if geo_classification == "non_eu":
        return "rejected", 0

    if remote_model == "remote_only":
        return "approved", 100

    if remote_model == "remote_region_locked":
        if geo_classification in {"eu_explicit", "eu_region"}:
            return "approved", 90
        return "rejected", 0

    if remote_model == "remote_optional":
        return "review", 60

    return "review", 50


def main():
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    job_id,
                    title,
                    description,
                    remote_scope,
                    remote_class
                FROM jobs
                WHERE source LIKE 'greenhouse:%'
            """)
        ).mappings().all()

    stats = Counter()

    for row in rows:
        remote_model = row["remote_class"]

        geo_result = classify_geo(
            title=row["title"] or "",
            description=row["description"] or "",
            remote_scope=row["remote_scope"] or "",
        )
        geo = geo_result["geo_class"]
        if hasattr(geo, "value"):
            geo = geo.value

        status, score = shadow_resolve(remote_model, geo)

        stats[status] += 1

    print("Shadow compliance results:")
    for k, v in stats.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
