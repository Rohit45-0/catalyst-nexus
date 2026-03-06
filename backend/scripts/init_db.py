import sys
import os

# Add the project root to sys.path so we can import 'backend.app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.app.db.base import Base, engine
from backend.app.db import models # This ensures models are registered with Base

def init_db():
    print("🚀 Initializing Catalyst Nexus Database...")
    try:
        # This creates all tables defined in models.py
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully in Supabase.")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

if __name__ == "__main__":
    init_db()
