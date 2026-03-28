import os

from sqlalchemy import create_engine


def get_database_url():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return database_url

    database_path = os.environ.get("DATABASE_PATH", "database.db")
    return f"sqlite:///{database_path}"


def create_db_engine():
    database_url = get_database_url()
    connect_args = {}

    if database_url.startswith("sqlite:///"):
        connect_args["check_same_thread"] = False

    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
