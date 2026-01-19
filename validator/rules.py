from datetime import timedelta

DEFAULT_TTL = timedelta(hours=48)

SOURCE_TTL_OVERRIDES = {
    "example_source": timedelta(hours=72),
}


def get_ttl_for_source(source_id: str) -> timedelta:
    return SOURCE_TTL_OVERRIDES.get(source_id, DEFAULT_TTL)
