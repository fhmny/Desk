"""Explicit first-time schema creation for a NEW, empty Desk database."""
from sqlalchemy import inspect

from app.main import Base, IS_PRODUCTION, engine


def main():
    existing = inspect(engine).get_table_names()
    if existing:
        raise SystemExit(f"Refusing to initialize a non-empty database ({len(existing)} tables found).")
    Base.metadata.create_all(engine)
    print(f"Created {len(Base.metadata.tables)} Desk tables in {'production' if IS_PRODUCTION else 'development'} database.")


if __name__ == "__main__":
    main()
