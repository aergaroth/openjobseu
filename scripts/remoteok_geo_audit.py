from collections import defaultdict, Counter
from sqlalchemy import text
from storage.db import get_engine

engine = get_engine()

SOURCE = "remoteok"

EU_KEYWORDS = [
    "eu",
    "europe",
    "european union",
    "eea",
    "united kingdom",
    "uk",
]

US_RESTRICTIONS = [
    "us only",
    "united states only",
    "us citizens",
    "us work authorization",
    "must reside in united states",
    "north america only",
    "canada only",
    "apac only",
]

NON_EU_SIGNALS = [
    "singapore",
    "india",
    "brazil",
    "mexico",
    "australia",
    "apj",
    "asia",
]

def contains_any(text: str, keywords: list[str]) -> bool:
    if not text:
        return False
    text = text.lower()
    return any(k in text for k in keywords)


def classify(row):
    scope = (row["remote_scope"] or "").lower()
    title = (row["title"] or "").lower()
    description = (row["description"] or "").lower()

    full_text = f"{scope} {title} {description}"

    # A) Explicit EU
    if contains_any(full_text, EU_KEYWORDS):
        return "EU_EXPLICIT"

    # C) Worldwide with US restrictions
    if contains_any(full_text, US_RESTRICTIONS):
        return "WORLDWIDE_US_RESTRICTED"

    # D) Clear non-EU signal
    if contains_any(title, NON_EU_SIGNALS):
        return "NON_EU_SIGNAL"

    # B) Worldwide without restrictions
    if scope == "worldwide":
        return "WORLDWIDE_OK"

    # E) Fallback
    return "UNCLEAR"


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
        category = classify(row)
        counter[category] += 1

        if len(examples[category]) < 5:
            examples[category].append(row["title"])

    print(f"\n=== GEO AUDIT FOR SOURCE: {SOURCE} ===")
    print(f"Total jobs: {total}\n")

    for category, count in counter.most_common():
        percent = (count / total) * 100 if total else 0
        print(f"{category}: {count} ({percent:.1f}%)")

    print("\n--- Example titles (max 5 per category) ---")
    for category, titles in examples.items():
        print(f"\n[{category}]")
        for t in titles:
            print(f"- {t}")

    # connection closed by context manager


if __name__ == "__main__":
    main()
