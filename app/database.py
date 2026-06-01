import logging
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from typing import Generator
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/tech_video_hub")
POSTGRES_MAINTENANCE_DB = os.getenv("POSTGRES_MAINTENANCE_DB", "postgres")
AUTO_CREATE_DATABASE = os.getenv("AUTO_CREATE_DATABASE", "true").lower() in {"1", "true", "yes", "on"}


def _normalize_database_url(database_url: str) -> str:
    """Use the project-standard Psycopg 3 dialect for PostgreSQL URLs."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    return database_url


DATABASE_URL = _normalize_database_url(RAW_DATABASE_URL)
logger.info(f"Database URL configured (host: {make_url(DATABASE_URL).host})")

try:
    engine = create_engine(DATABASE_URL)
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[SessionLocal, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _validate_postgres_url(database_url: str) -> URL:
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        raise ValueError("DATABASE_URL must use PostgreSQL, for example postgresql+psycopg://user:password@host:5432/dbname")
    if not url.database:
        raise ValueError("DATABASE_URL must include the target database name")
    return url



def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def ensure_database_exists() -> None:
    """Create the configured PostgreSQL database when it does not exist yet."""
    try:
        target_url = _validate_postgres_url(DATABASE_URL)
        admin_url = target_url.set(database=POSTGRES_MAINTENANCE_DB)
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

        try:
            with admin_engine.connect() as connection:
                logger.info(f"Checking if database '{target_url.database}' exists...")
                exists = connection.scalar(
                    text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                    {"database_name": target_url.database},
                )
                if not exists:
                    logger.info(f"Creating database '{target_url.database}'...")
                    connection.exec_driver_sql(f"CREATE DATABASE {_quoted_identifier(target_url.database)}")
                    logger.info(f"Database '{target_url.database}' created successfully")
                else:
                    logger.info(f"Database '{target_url.database}' already exists")
        finally:
            admin_engine.dispose()
    except Exception as e:
        logger.error(f"Error ensuring database exists: {e}", exc_info=True)
        raise


def run_migrations() -> None:
    """Apply pending Alembic migrations to the configured database."""
    try:
        from alembic import command

        logger.info("Running database migrations...")
        alembic_config = _alembic_config()
        adopt_existing_schema(alembic_config)
        command.upgrade(alembic_config, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}", exc_info=True)
        raise


def _alembic_config():
    from alembic.config import Config

    alembic_config = Config(str(BASE_DIR / "alembic.ini"))
    # ConfigParser treats percent signs as interpolation markers, while database
    # URLs legitimately use them for encoded characters such as `%40` in passwords.
    alembic_config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
    return alembic_config


def adopt_existing_schema(alembic_config) -> None:
    """Mark legacy create_all schemas as migrated when they already match the app."""
    try:
        from alembic import command

        expected_tables = {
            "categories",
            "playlists",
            "videos",
            "comments",
            "likes",
            "channels",
            "freelancer_profiles",
        }
        with engine.connect() as connection:
            inspector = inspect(connection)
            existing_tables = set(inspector.get_table_names())
            if "alembic_version" in existing_tables or not expected_tables.issubset(existing_tables):
                logger.debug("Schema adoption: migrations already applied or tables incomplete")
                return

            expected_columns = {table.name: set(table.columns.keys()) for table in Base.metadata.sorted_tables}
            if any(
                expected_columns[table] - {column["name"] for column in inspector.get_columns(table)}
                for table in expected_tables
            ):
                logger.debug("Schema adoption: column mismatch detected")
                return

        logger.info("Stamping existing schema as migrated")
        command.stamp(alembic_config, "head")
    except Exception as e:
        logger.warning(f"Could not adopt existing schema: {e}")
        # Don't raise - this is a non-critical operation


def initialize_database() -> None:
    """Ensure the PostgreSQL database exists and is migrated before use."""
    try:
        logger.info(f"Initializing database (AUTO_CREATE_DATABASE={AUTO_CREATE_DATABASE})...")
        if AUTO_CREATE_DATABASE:
            ensure_database_exists()
        run_migrations()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Critical error during database initialization: {e}", exc_info=True)
        raise
