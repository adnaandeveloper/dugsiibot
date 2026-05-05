import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    with get_conn() as conn, conn.cursor() as cur:
        with open("schema.sql","r") as f:
            cur.execute(f.read())
        conn.commit()