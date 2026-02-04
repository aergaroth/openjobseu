import os
import tempfile
from storage.sqlite import init_db

def pytest_sessionstart(session):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    os.environ["OPENJOBSEU_DB_PATH"] = path
    init_db()