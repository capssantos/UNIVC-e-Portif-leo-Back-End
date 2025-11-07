import os
import psycopg2
import psycopg2.extras

def _compose_dsn():
    dsn = os.getenv("PG_DSN")
    if dsn:
        return dsn
    user = os.getenv("USER") or os.getenv("PGUSER")
    pwd  = os.getenv("PASSWORD") or os.getenv("PGPASSWORD")
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "5432")
    db   = os.getenv("DBNAME")
    ssl  = os.getenv("PGSSLMODE", "require")  # "disable", "require", etc.
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={ssl}"

def get_conn():
    dsn = _compose_dsn()
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)

def one(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchone()

def many(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()

def run(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        try:
            return cur.fetchone()
        except psycopg2.ProgrammingError:
            return None
