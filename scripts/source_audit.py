import sqlite3
import re
from collections import Counter, defaultdict

DB_PATH = "data/openjobseu.db"
SOURCE = "remoteok"  # zmień na inne źródło do audytu

# --- heurystyki do audytu ---

NON_EU_TITLE_KEYWORDS = [
    "singapore",
    "usa",
    "united states",
    "canada",
    "australia",
    "india",
    "apj",
    "asia",
]

HARD_RESTRICTIONS = [
    "us only",
    "united states only",
    "us citizens",
    "us work authorization",
    "north america only",
    "canada only",
    "apac only",
]

SPAM_MARKERS = [
    "mention the word",
    "beta feature to avoid spam",
    "RMTg",  # base64-like tags often in RemoteOK
]


def contains_any(text: str, keywords: list[str]) -> bool:
    if not text:
        return False
    text = text.lower()
    return any(k in text for k in keywords)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE source = ?", (SOURCE,))
    rows = cur.fetchall()

    total = len(rows)
    print(f"\n=== AUDIT FOR SOURCE: {SOURCE} ===")
    print(f"Total jobs: {total}")

    scope_counter = Counter()
    title_geo_hits = 0
    hard_restrictions_hits = 0
    spam_hits = 0

    flagged_examples = defaultdict(list)

    for row in rows:
        scope = (row["remote_scope"] or "").lower()
        title = row["title"] or ""
        description = row["description"] or ""

        scope_counter[scope] += 1

        if contains_any(title, NON_EU_TITLE_KEYWORDS):
            title_geo_hits += 1
            flagged_examples["title_geo"].append(title)

        if contains_any(description, HARD_RESTRICTIONS):
            hard_restrictions_hits += 1
            flagged_examples["hard_restrictions"].append(title)

        if contains_any(description, SPAM_MARKERS):
            spam_hits += 1
            flagged_examples["spam"].append(title)

    print("\n--- Remote scope breakdown ---")
    for scope, count in scope_counter.most_common():
        print(f"{scope or 'NONE'}: {count}")

    print("\n--- Heuristic signals ---")
    print(f"Title non-EU keywords: {title_geo_hits}")
    print(f"Hard geo restrictions: {hard_restrictions_hits}")
    print(f"Spam markers: {spam_hits}")

    print("\n--- Example flagged titles (max 5 per category) ---")
    for category, titles in flagged_examples.items():
        print(f"\n[{category}]")
        for t in titles[:5]:
            print(f"- {t}")

    conn.close()


if __name__ == "__main__":
    main()
