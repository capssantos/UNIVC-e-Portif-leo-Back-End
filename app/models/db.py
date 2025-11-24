import os
import psycopg2
import psycopg2.extras
from uuid import UUID 

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

def _normalize_params(params: dict | None):
    """
    Converte tipos não adaptados (como uuid.UUID) para algo
    que o psycopg2 saiba lidar (ex: str).
    """
    if not params:
        return {}
    norm = {}
    for k, v in params.items():
        if isinstance(v, UUID):
            norm[k] = str(v)
        else:
            norm[k] = v
    return norm

def one(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, _normalize_params(params))
        return cur.fetchone()

def many(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, _normalize_params(params))
        return cur.fetchall()

def run(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, _normalize_params(params))
        try:
            return cur.fetchone()
        except psycopg2.ProgrammingError:
            return None
