import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers(
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    pricing_type TEXT DEFAULT 'hourly',
                    hourly_rate INT DEFAULT 0,
                    monthly_price INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS lessons(
                    id SERIAL PRIMARY KEY,
                    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
                    amount INT NOT NULL,
                    hours NUMERIC(3,1) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT now(),
                    invoiced BOOLEAN DEFAULT false
                );
                CREATE TABLE IF NOT EXISTS payments(
                    id SERIAL PRIMARY KEY,
                    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
                    amount INT NOT NULL,
                    status TEXT DEFAULT 'betalt',
                    paid_at TIMESTAMP DEFAULT now()
                );
            """)
            # FIX gamle tabeller
            cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP DEFAULT now();")
            cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS invoiced BOOLEAN DEFAULT false;")
            cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS hours NUMERIC(3,1) DEFAULT 0;")
            cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS hourly_rate INT DEFAULT 0;")
            cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS monthly_price INT DEFAULT 0;")
        conn.commit()