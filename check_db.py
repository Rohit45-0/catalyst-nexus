
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def check_db_connection():
    print("🔌 Checking Database Connection...")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL is missing in .env file")
        return

    # Mask password for display
    masked_url = DATABASE_URL
    if ":" in DATABASE_URL and "@" in DATABASE_URL:
        try:
             part1 = DATABASE_URL.split("@")[0]
             part2 = DATABASE_URL.split("@")[1]
             user_pass = part1.split("://")[1]
             if ":" in user_pass:
                 user = user_pass.split(":")[0]
                 masked_url = f"{part1.split('://')[0]}://{user}:****@{part2}"
        except:
             pass
    
    print(f"   URL: {masked_url}")

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            
            # Check if users table exists
            try:
                result = connection.execute(text("SELECT count(*) FROM users"))
                count = result.scalar()
                print(f"✅ Users table found. Total users: {count}")
                
                # Check specifically for demo user
                result = connection.execute(text("SELECT email, is_active FROM users WHERE email='rohit.demo.catalyst@gmail.com'"))
                user = result.fetchone()
                if user:
                    print(f"✅ Demo user 'rohit.demo.catalyst@gmail.com' found! (Active: {user[1]})")
                else:
                    print("❌ Demo user 'rohit.demo.catalyst@gmail.com' NOT found.")
                    print("   👉 Run: python backend/create_demo_user.py")
            except Exception as e:
                print(f"⚠️  Could not query users table: {e}")
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    check_db_connection()
