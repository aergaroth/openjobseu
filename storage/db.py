import os
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine import Engine

_engine: Engine | None = None


def _create_cloud_sql_engine() -> Engine:
    from google.cloud.sql.connector import Connector

    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]
    db_name = os.environ["DB_NAME"]
    db_user = os.environ["DB_USER"]

    connector = Connector()

    def getconn():
        return connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            db=db_name,
            enable_iam_auth=True,
        )

    return sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        pool_timeout=30,
        pool_recycle=1800,
        future=True,
    )


def _create_standard_postgres_engine(database_url: str) -> Engine:
    return sqlalchemy.create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": 10

        },
        future=True,
    )


def _resolve_engine() -> Engine:
    db_mode = os.getenv("DB_MODE")

    if not db_mode:
        raise RuntimeError("DB_MODE is not set (expected 'cloudsql' or 'standard').")

    if db_mode == "cloudsql":
        return _create_cloud_sql_engine()

    if db_mode == "standard":
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL must be set in DB_MODE=standard.")
        if not database_url.startswith("postgresql+psycopg://"):
            raise RuntimeError("DATABASE_URL must use postgresql+psycopg://")
        return _create_standard_postgres_engine(database_url)
    


    raise RuntimeError(f"Unsupported DB_MODE: {db_mode}")


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _resolve_engine()
    return _engine


def db_healthcheck() -> None:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))