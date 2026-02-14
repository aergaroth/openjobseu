import sqlite3
from collections import defaultdict, Counter

DB_PATH = "data/openjobseu.db"
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE source = ?", (SOURCE,))
    rows = cur.fetchall()

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

    conn.close()


if __name__ == "__main__":
    main()
