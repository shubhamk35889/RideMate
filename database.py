import os

from sqlalchemy import create_engine


def _default_sqlite_path():
    # Vercel serverless functions can only write to /tmp at runtime.
    if os.environ.get("VERCEL"):
        return "/tmp/database.db"
    return "database.db"


def get_database_url():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return database_url

    database_path = os.environ.get("DATABASE_PATH", _default_sqlite_path())
    return f"sqlite:///{database_path}"


def create_db_engine():
    database_url = get_database_url()
    connect_args = {}

    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(sqlite_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        connect_args["check_same_thread"] = False

    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
