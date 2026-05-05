import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    pricing_type TEXT DEFAULT 'hourly',
                    hourly_rate INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
                    hours REAL DEFAULT 1,
                    amount INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT now(),
                    invoiced BOOLEAN DEFAULT false
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
                    amount INTEGER NOT NULL,
                    status TEXT DEFAULT 'paid',
                    paid_at TIMESTAMP DEFAULT now()
                );
            """)
            # migrations
            cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS hourly_rate INTEGER DEFAULT 0;")
            cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now();")
            cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS invoiced BOOLEAN DEFAULT false;")
            cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'paid';")
            cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP DEFAULT now();")
            cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS method TEXT DEFAULT 'kontant';")
        conn.commit()