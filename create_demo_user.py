

import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

with open("user_creation_result.txt", "w", encoding="utf-8") as f:
    try:
        from backend.app.db.base import SessionLocal
        from backend.app.db.models import User
        from backend.app.core.security import get_password_hash
        
        db = SessionLocal()
        email = "rohit.demo.catalyst@gmail.com"
        username = "rohit_demo"
        password = "password123"
        
        user = db.query(User).filter(User.email == email).first()
        if user:
            msg = f"User {email} already exists.\n"
            print(msg)
            f.write(msg)
            # Update password just in case
            user.hashed_password = get_password_hash(password)
            user.is_active = True
            db.commit()
            msg = f"✅ Password reset to: {password}\n"
            print(msg)
            f.write(msg)
        else:
            hashed_password = get_password_hash(password)
            new_user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True
            )
            db.add(new_user)
            db.commit()
            msg = f"✅ User {email} created successfully.\n"
            print(msg)
            f.write(msg)
            msg = f"Password: {password}\n"
            print(msg)
            f.write(msg)
            
        db.close()

    except Exception as e:
        import traceback
        err = f"❌ Error: {e}\n{traceback.format_exc()}"
        print(err)
        f.write(err)

if __name__ == "__main__":
    pass

