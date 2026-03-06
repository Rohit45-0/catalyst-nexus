import psycopg2

url = 'postgresql://postgres.ypvensjulitirpcsxekr:MH12XV9450%40@db.ypvensjulitirpcsxekr.supabase.co:5432/postgres'

with open('migration_output.txt', 'w') as f:
    try:
        f.write('Connecting to DB...\n')
        conn = psycopg2.connect(url, connect_timeout=15)
        conn.autocommit = True
        f.write('Connected\n')
        cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';")
        cols = [r[0] for r in cur.fetchall()]
        f.write(f'Existing cols: {cols}\n')
        for col in ['company_name', 'product_category', 'target_audience', 'date_of_birth']:
            if col not in cols:
                f.write(f'Adding {col}...\n')
                cur.execute(f'ALTER TABLE users ADD COLUMN {col} VARCHAR;')
                f.write(f'Done {col}\n')
        cur.close()
        conn.close()
        f.write('SUCCESS\n')
    except Exception as e:
        f.write(f'ERROR: {str(e)}\n')
