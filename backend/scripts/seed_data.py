"""
Data Seeding Script
==================

Seed the database with initial data for development/testing.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.db.base import get_db_session
from backend.app.db.models import User, Project
from backend.app.core.security import get_password_hash


async def seed_users():
    """Create seed users."""
    print("Seeding users...")
    
    users_data = [
        {
            "email": "admin@catalyst.nexus",
            "username": "admin",
            "password": "admin123456",
            "full_name": "System Administrator",
            "is_superuser": True,
            "is_verified": True,
        },
        {
            "email": "demo@catalyst.nexus",
            "username": "demo",
            "password": "demo123456",
            "full_name": "Demo User",
            "is_superuser": False,
            "is_verified": True,
        },
    ]
    
    async with get_db_session() as db:
        for user_data in users_data:
            existing = await User.get_by_email(db, user_data["email"])
            if existing:
                print(f"  User {user_data['email']} already exists, skipping...")
                continue
            
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                is_superuser=user_data["is_superuser"],
                is_verified=user_data["is_verified"],
            )
            db.add(user)
            print(f"  Created user: {user_data['email']}")
        
        await db.commit()
    
    print("Users seeded successfully!")


async def seed_projects():
    """Create seed projects for demo user."""
    print("Seeding projects...")
    
    async with get_db_session() as db:
        demo_user = await User.get_by_email(db, "demo@catalyst.nexus")
        
        if not demo_user:
            print("  Demo user not found, skipping projects...")
            return
        
        projects_data = [
            {
                "name": "Sample Video Project",
                "description": "A demonstration project for video generation",
                "settings": {
                    "default_resolution": "1080p",
                    "default_fps": 24,
                },
            },
            {
                "name": "Character Design",
                "description": "Identity vault testing project",
                "settings": {
                    "identity_type": "character",
                },
            },
        ]
        
        for project_data in projects_data:
            project = Project(
                name=project_data["name"],
                description=project_data["description"],
                settings=project_data["settings"],
                owner_id=demo_user.id,
            )
            db.add(project)
            print(f"  Created project: {project_data['name']}")
        
        await db.commit()
    
    print("Projects seeded successfully!")


async def seed_all():
    """Run all seed functions."""
    print("=" * 50)
    print("Starting database seeding...")
    print("=" * 50)
    
    await seed_users()
    await seed_projects()
    
    print("=" * 50)
    print("Database seeding complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed_all())
