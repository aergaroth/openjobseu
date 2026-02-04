import os
import tempfile

db_fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(db_fd)
os.environ["OPENJOBSEU_DB_PATH"] = db_path