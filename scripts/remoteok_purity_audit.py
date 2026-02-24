from collections import Counter, defaultdict
from sqlalchemy import text
from storage.db import get_engine

engine = get_engine()  

SOURCE = "remoteok"

NON_REMOTE_KEYWORDS = [
    "onsite",
    "on-site",
    "in office",
    "in-office",
    "hybrid",
    "based in",
    "must be located in",
    "relocation",
]

def contains_any(text: str, keywords: list[str]) -> bool:
    if not text:
        return False
    text = text.lower()
    return any(k in text for k in keywords)


def location_suspicious(location: str) -> bool:
    if not location:
        return False

    location = location.lower()

    # If location explicitly says remote/worldwide → ok
    if any(x in location for x in ["remote", "anywhere", "worldwide"]):
        return False

    # If location looks like a real city/state → suspicious
    if "," in location or len(location.split()) >= 2:
        return True

    return False


def main():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM jobs WHERE source = :source"),
            {"source": SOURCE},
        ).mappings().all()

    total = len(rows)
    counter = Counter()
    examples = defaultdict(list)

    for row in rows:
        title = (row["title"] or "").lower()
        description = (row["description"] or "").lower()
        location = (row["remote_scope"] or "")  # remote_scope used as location proxy

        full_text = f"{title} {description}"

        non_remote_signal = contains_any(full_text, NON_REMOTE_KEYWORDS)
        suspicious_location = location_suspicious(location)

        if non_remote_signal or suspicious_location:
            category = "LIKELY_NOT_REMOTE"
        else:
            category = "LIKELY_REMOTE"

        counter[category] += 1

        if len(examples[category]) < 5:
            examples[category].append(row["title"])

    print(f"\n=== REMOTE PURITY AUDIT FOR SOURCE: {SOURCE} ===")
    print(f"Total jobs: {total}\n")

    for category, count in counter.items():
        percent = (count / total) * 100 if total else 0
        print(f"{category}: {count} ({percent:.1f}%)")

    print("\n--- Example titles ---")
    for category, titles in examples.items():
        print(f"\n[{category}]")
        for t in titles:
            print(f"- {t}")

    # connection closed by context manager


if __name__ == "__main__":
    main()
