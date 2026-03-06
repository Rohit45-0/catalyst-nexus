
import sys
import os

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from backend.app.db.base import engine


def ensure_column(conn, table_name: str, column_name: str, alter_sql: str):
    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name=:table_name AND column_name=:column_name"
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    if not result.fetchone():
        print(f"Adding {table_name}.{column_name} ...")
        conn.execute(text(alter_sql))
    else:
        print(f"{table_name}.{column_name} already exists.")


def migrate():
    print("Migrating database schema...")
    with engine.connect() as conn:
        try:
            # Users compatibility columns
            ensure_column(conn, "users", "username", "ALTER TABLE users ADD COLUMN username VARCHAR")
            ensure_column(conn, "users", "full_name", "ALTER TABLE users ADD COLUMN full_name VARCHAR")
            ensure_column(conn, "users", "avatar_url", "ALTER TABLE users ADD COLUMN avatar_url VARCHAR")
            ensure_column(conn, "users", "is_verified", "ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE")
            ensure_column(conn, "users", "is_superuser", "ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE")
            ensure_column(conn, "users", "updated_at", "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()")
            ensure_column(conn, "users", "wallet_balance", "ALTER TABLE users ADD COLUMN wallet_balance INTEGER NOT NULL DEFAULT 500")

            # Legacy instagram columns used by scripts
            ensure_column(conn, "users", "instagram_access_token", "ALTER TABLE users ADD COLUMN instagram_access_token VARCHAR")
            ensure_column(conn, "users", "instagram_page_id", "ALTER TABLE users ADD COLUMN instagram_page_id VARCHAR")
            ensure_column(conn, "users", "instagram_page_name", "ALTER TABLE users ADD COLUMN instagram_page_name VARCHAR")

            # Projects compatibility columns
            ensure_column(conn, "projects", "name", "ALTER TABLE projects ADD COLUMN name VARCHAR")
            ensure_column(conn, "projects", "settings", "ALTER TABLE projects ADD COLUMN settings JSONB DEFAULT '{}'::jsonb")
            ensure_column(conn, "projects", "is_archived", "ALTER TABLE projects ADD COLUMN is_archived BOOLEAN DEFAULT FALSE")
            ensure_column(conn, "projects", "thumbnail_url", "ALTER TABLE projects ADD COLUMN thumbnail_url VARCHAR")
            ensure_column(conn, "projects", "updated_at", "ALTER TABLE projects ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()")

            # Jobs compatibility columns
            ensure_column(conn, "jobs", "user_id", "ALTER TABLE jobs ADD COLUMN user_id UUID")
            ensure_column(conn, "jobs", "parameters", "ALTER TABLE jobs ADD COLUMN parameters JSONB DEFAULT '{}'::jsonb")
            ensure_column(conn, "jobs", "result", "ALTER TABLE jobs ADD COLUMN result JSONB")
            ensure_column(conn, "jobs", "output_assets", "ALTER TABLE jobs ADD COLUMN output_assets JSONB DEFAULT '[]'::jsonb")
            ensure_column(conn, "jobs", "progress", "ALTER TABLE jobs ADD COLUMN progress INTEGER DEFAULT 0")
            ensure_column(conn, "jobs", "status_message", "ALTER TABLE jobs ADD COLUMN status_message VARCHAR")
            ensure_column(conn, "jobs", "error", "ALTER TABLE jobs ADD COLUMN error VARCHAR")
            ensure_column(conn, "jobs", "priority", "ALTER TABLE jobs ADD COLUMN priority INTEGER DEFAULT 5")
            ensure_column(conn, "jobs", "retry_count", "ALTER TABLE jobs ADD COLUMN retry_count INTEGER DEFAULT 0")
            ensure_column(conn, "jobs", "started_at", "ALTER TABLE jobs ADD COLUMN started_at TIMESTAMP")
            ensure_column(conn, "jobs", "completed_at", "ALTER TABLE jobs ADD COLUMN completed_at TIMESTAMP")

            # Campaign analytics/GNN compatibility columns
            ensure_column(conn, "campaigns", "category", "ALTER TABLE campaigns ADD COLUMN category VARCHAR DEFAULT 'General'")
            ensure_column(conn, "campaigns", "content_features", "ALTER TABLE campaigns ADD COLUMN content_features JSONB")
            ensure_column(conn, "insight_snapshots", "content_boost", "ALTER TABLE insight_snapshots ADD COLUMN content_boost FLOAT DEFAULT 1.0")

            # Ensure GNN/analytics extension tables exist for ingestion pipeline
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS category_content_profiles (
                    id UUID PRIMARY KEY,
                    category VARCHAR NOT NULL UNIQUE,
                    locale VARCHAR NOT NULL DEFAULT 'IN',
                    top_keywords JSONB DEFAULT '[]'::jsonb,
                    common_hook_lines JSONB DEFAULT '[]'::jsonb,
                    common_cta_lines JSONB DEFAULT '[]'::jsonb,
                    common_phrases JSONB DEFAULT '[]'::jsonb,
                    sample_video_count INTEGER DEFAULT 0,
                    avg_engagement_rate FLOAT DEFAULT 0.0,
                    last_data_source VARCHAR,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS campaign_content_features (
                    id UUID PRIMARY KEY,
                    campaign_id VARCHAR NOT NULL,
                    category_profile_id UUID,
                    category VARCHAR NOT NULL,
                    platform VARCHAR DEFAULT 'youtube',
                    region_code VARCHAR DEFAULT 'IN',
                    data_source VARCHAR,
                    sampled_video_ids JSONB DEFAULT '[]'::jsonb,
                    sampled_video_titles JSONB DEFAULT '[]'::jsonb,
                    transcript_video_count INTEGER DEFAULT 0,
                    trend_keywords JSONB DEFAULT '[]'::jsonb,
                    trend_hooks JSONB DEFAULT '[]'::jsonb,
                    content_gaps JSONB DEFAULT '[]'::jsonb,
                    transcript_phrases JSONB DEFAULT '[]'::jsonb,
                    avg_views FLOAT DEFAULT 0.0,
                    avg_likes FLOAT DEFAULT 0.0,
                    avg_comments FLOAT DEFAULT 0.0,
                    avg_engagement_rate FLOAT DEFAULT 0.0,
                    hook_density FLOAT DEFAULT 0.0,
                    cta_density FLOAT DEFAULT 0.0,
                    feature_vector JSONB DEFAULT '[]'::jsonb,
                    notes TEXT,
                    is_training_ready BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_category_profile_category ON category_content_profiles (category)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_campaign_content_campaign ON campaign_content_features (campaign_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_campaign_content_category ON campaign_content_features (category)"))

            conn.commit()
            print("Migration successful!")
        except Exception as e:
            conn.rollback()
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
