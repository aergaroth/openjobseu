#!/usr/bin/env python3
"""
Scans the database for job descriptions that still contain unescaped HTML tags 
after the normal ATS extraction process, outputting the most common leftover tags.
"""

import os
import sys
import re
from collections import Counter

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from storage.db_engine import get_engine

def main():
    engine = get_engine()
    html_tag_pattern = re.compile(r"<[^>]+>")

    print("Pobieranie ofert z bazy danych...")
    with engine.connect() as conn:
        # Pobieramy tylko te opisy, które w ogóle mają znak '<' i '>', by nie obciążać pamięci
        rows = conn.execute(
            text("SELECT job_id, source, company_name, description FROM jobs WHERE description LIKE '%<%>%'")
        ).mappings().all()

    results = []
    for row in rows:
        desc = row["description"] or ""
        tags = html_tag_pattern.findall(desc)
        if tags:
            results.append({
                "job_id": row["job_id"],
                "source": row["source"],
                "company_name": row["company_name"],
                "tag_count": len(tags),
                "tags_found": Counter(tags).most_common(5) # Top 5 najczęstszych tagów w tej ofercie
            })
    
    # Sortujemy malejąco po liczbie znalezionych tagów
    results.sort(key=lambda x: x["tag_count"], reverse=True)

    print(f"\nZnaleziono {len(results)} ofert z pozostałościami po HTML.\n")
    print(f"{'JOB ID':<35} | {'SOURCE':<15} | {'TAG COUNT':<10} | TOP TAGS")
    print("-" * 100)
    
    for res in results[:50]:
        tags_str = ", ".join(f"{t}: {c}" for t, c in res["tags_found"])
        print(f"{res['job_id']:<35} | {res['source']:<15} | {res['tag_count']:<10} | {tags_str}")

if __name__ == "__main__":
    main()