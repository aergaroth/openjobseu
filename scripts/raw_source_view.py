from sqlalchemy import text
from storage.db import get_engine

engine = get_engine()

with engine.connect() as conn:
	row = conn.execute(
		text("SELECT description FROM jobs WHERE source = :source LIMIT 1"),
		{"source": "remoteok"},
	).mappings().first()

if row:
	print(repr(row["description"]))
