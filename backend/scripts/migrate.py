"""
Database Migration Script
=========================

Run database migrations using Alembic.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.db.base import engine, Base
from backend.app.db import models  # noqa: F401
from backend.app.db import gnn_models  # noqa: F401


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    
    with engine.begin() as conn:
        Base.metadata.create_all(bind=engine)
    
    print("Tables created successfully!")


def drop_tables():
    """Drop all database tables."""
    print("Dropping database tables...")
    
    with engine.begin() as conn:
        Base.metadata.drop_all(bind=engine)
    
    print("Tables dropped successfully!")


def reset_database():
    """Reset the database by dropping and recreating all tables."""
    drop_tables()
    create_tables()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration script")
    parser.add_argument(
        "action",
        choices=["create", "drop", "reset"],
        help="Migration action to perform"
    )
    
    args = parser.parse_args()
    
    if args.action == "create":
        create_tables()
    elif args.action == "drop":
        drop_tables()
    elif args.action == "reset":
        reset_database()
