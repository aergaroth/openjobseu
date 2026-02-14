import sqlite3

conn = sqlite3.connect("data/openjobseu.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT description FROM jobs WHERE source='remoteok' LIMIT 1")
row = cur.fetchone()

print(repr(row["description"]))
