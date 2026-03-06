
import sys
import os
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.db.base import SessionLocal, Base, engine
from backend.app.db.models import User
from backend.app.core.security import get_password_hash

def create_demo_user():
    # Ensure tables exist (in case DB is fresh)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    email = "rohit.demo.catalyst@gmail.com"
    password = "password" 
    
    print(f"🔄 Setting up demo user: {email}")
    
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"   User exists! Resetting password...")
            user.hashed_password = get_password_hash(password)
            user.is_active = True
            db.commit()
            print(f"   ✅ Password reset to: '{password}'")
        else:
            print(f"   Creating new user...")
            new_user = User(
                email=email,
                username="rohit_demo",
                hashed_password=get_password_hash(password),
                full_name="Rohit Demo",
                is_active=True
            )
            db.add(new_user)
            db.commit()
            print(f"   ✅ User created successfully!")
            print(f"   🔑 Login with: '{password}'")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_demo_user()
