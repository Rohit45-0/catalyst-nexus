
import psycopg2
import os
import sys
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL')
print(f"Connecting to: {url.split('@')[-1]}") # Log host only for safety

try:
    conn = psycopg2.connect(url, connect_timeout=10)
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';")
    cols = [r[0] for r in cur.fetchall()]
    print(f"Current columns: {cols}")
    
    needed = ['company_name', 'product_category', 'target_audience', 'date_of_birth']
    for col in needed:
        if col not in cols:
            print(f"Adding column {col}...")
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} VARCHAR;")
            print(f"Column {col} added.")
        else:
            print(f"Column {col} already exists.")
            
    cur.close()
    conn.close()
    print("Migration check complete.")
except Exception as e:
    print(f"FATAL ERROR: {e}")
    sys.exit(1)
