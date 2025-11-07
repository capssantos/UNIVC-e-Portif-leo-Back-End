import os
import glob
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

try:
    from dotenv import load_dotenv 
    load_dotenv()
except Exception:
    pass

def build_dsn() -> str:
    """
    Monta o DSN a partir de:
    1) DATABASE_URL (se existir), senão
    2) DBNAME/USER/PASSWORD/HOST/PORT do .env/ambiente.

    Lança erro se faltar alguma variável essencial.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.strip():
        return database_url.strip()

    dbname = os.getenv("DBNAME", "").strip()
    user = os.getenv("USER", "").strip()
    password = os.getenv("PASSWORD", "").strip()
    host = os.getenv("HOST", "").strip()
    port = os.getenv("PORT", "5432").strip()

    missing = [k for k, v in {
        "DBNAME": dbname,
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": port,
    }.items() if not v]
    if missing:
        raise RuntimeError(
            f"Variáveis ausentes no ambiente: {', '.join(missing)}. "
            "Preencha o .env ou exporte-as (ou use DATABASE_URL)."
        )

    return f"dbname={dbname} user={user} password={password} host={host} port={port}"


PG_DSN = build_dsn()

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def get_conn():
    return psycopg2.connect(PG_DSN)


def ensure_schema_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version     TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                direction   TEXT NOT NULL,        -- 'up' ou 'down'
                applied_at  TIMESTAMP NOT NULL
            )
            """
        )
    conn.commit()


def list_migration_files(direction="up"):
    pattern = os.path.join(MIGRATIONS_DIR, f"*.{direction}.sql")
    files = sorted(glob.glob(pattern))  # sorted garante ordem 0001, 0002, ...
    return files


def get_applied_versions(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT version FROM schema_migrations WHERE direction='up'")
        rows = cur.fetchall()
    return {r["version"] for r in rows}


def parse_version_and_name(filepath):
    """Ex.: '.../0001_create_usuarios.up.sql' -> ('0001', 'create_usuarios')"""
    base = os.path.basename(filepath)
    # 0001_create_usuarios.up.sql
    parts = base.split("_", 1)
    version = parts[0]
    name = parts[1].split(".")[0]  # create_usuarios.up
    name = name.rsplit(".", 1)[0]  # create_usuarios
    return version, name


def apply_sql(conn, sql_text):
    with conn.cursor() as cur:
        cur.execute(sql_text)
    conn.commit()


def migrate_up():
    conn = get_conn()
    try:
        ensure_schema_table(conn)
        applied = get_applied_versions(conn)
        files = list_migration_files("up")
        to_apply = []
        for f in files:
            version, _ = parse_version_and_name(f)
            if version not in applied:
                to_apply.append(f)

        if not to_apply:
            print("✅ Não há novas migrations para aplicar.")
            return

        for fpath in to_apply:
            version, name = parse_version_and_name(fpath)
            print(f"▶️  Aplicando {version} — {name} (up)")
            with open(fpath, "r", encoding="utf-8") as f:
                sql = f.read()
            apply_sql(conn, sql)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO schema_migrations (version, name, direction, applied_at)
                    VALUES (%s, %s, 'up', %s)
                    """,
                    (version, name, datetime.utcnow()),
                )
            conn.commit()

        print("🎉 Migração concluída.")
    finally:
        conn.close()


def migrate_down(steps=1):
    """
    Reverte as últimas `steps` migrations (na ordem inversa).
    """
    conn = get_conn()
    try:
        ensure_schema_table(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT version, name
                FROM schema_migrations
                WHERE direction='up'
                ORDER BY applied_at DESC
                LIMIT %s
                """,
                (steps,),
            )
            last = cur.fetchall()

        if not last:
            print("⚠️  Não há migrations 'up' para reverter.")
            return

        for row in last:
            version = row["version"]
            name = row["name"]
            down_file = os.path.join(MIGRATIONS_DIR, f"{version}_{name}.down.sql")
            if not os.path.exists(down_file):
                raise FileNotFoundError(
                    f"Arquivo de rollback não encontrado: {down_file}"
                )

            print(f"⏪ Revertendo {version} — {name} (down)")
            with open(down_file, "r", encoding="utf-8") as f:
                sql = f.read()
            apply_sql(conn, sql)

            # Marca o rollback (e remove o 'up' se preferir manter limpa)
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM schema_migrations WHERE version=%s AND direction='up'",
                    (version,),
                )
                cur.execute(
                    """
                    INSERT INTO schema_migrations (version, name, direction, applied_at)
                    VALUES (%s, %s, 'down', %s)
                    """,
                    (version, name, datetime.utcnow()),
                )
            conn.commit()

        print("✅ Rollback concluído.")
    finally:
        conn.close()


def status():
    conn = get_conn()
    try:
        ensure_schema_table(conn)
        applied = get_applied_versions(conn)
        files = list_migration_files("up")
        print("== STATUS ==")
        for f in files:
            version, name = parse_version_and_name(f)
            mark = "APLICADA" if version in applied else "PENDENTE"
            print(f"{version} — {name:25} {mark}")
    finally:
        conn.close()

def _find_down_file(version: str, name: str) -> str:
    """Retorna o caminho do arquivo <version>_<name>.down.sql se existir."""
    candidate = os.path.join(MIGRATIONS_DIR, f"{version}_{name}.down.sql")
    return candidate if os.path.exists(candidate) else ""


def _list_all_down_files_reverse():
    """Lista TODOS os *.down.sql em ordem reversa (ex.: 0003, 0002, 0001)."""
    pattern = os.path.join(MIGRATIONS_DIR, "*_*.down.sql")
    files = sorted(glob.glob(pattern), reverse=True)
    return files


def reset():
    """
    Executa TODOS os downs em ordem reversa.
    - Se houver schema_migrations: usa a ordem real aplicada (applied_at DESC).
    - Se não houver: usa a ordem por filename (reverse sort).
    Sempre tenta continuar mesmo que uma down falhe (SAVEPOINT).
    """
    conn = get_conn()
    try:
        # Verifica se schema_migrations existe
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'schema_migrations'
                )
            """)
            (has_schema_migrations,) = cur.fetchone()

        down_queue = []

        if has_schema_migrations:
            # Busca as versões realmente aplicadas (ordem real)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT version, name
                    FROM schema_migrations
                    WHERE direction='up'
                    ORDER BY applied_at DESC
                """)
                rows = cur.fetchall()

            for r in rows:
                version, name = r["version"], r["name"]
                down_file = _find_down_file(version, name)
                if down_file:
                    down_queue.append((version, name, down_file))
                else:
                    print(f"⚠️  Down não encontrado para {version}_{name}. Ignorando.")

        else:
            # Fallback: não há registro; usa todos os downs do diretório em ordem reversa
            for f in _list_all_down_files_reverse():
                v, n = parse_version_and_name(f)  # reaproveita helper existente
                down_queue.append((v, n, f))

        if not down_queue:
            print("ℹ️  Nenhum arquivo .down.sql encontrado. Nada a fazer.")
        else:
            print("🧹 Iniciando RESET (executando downs em ordem reversa):")
            with conn.cursor() as cur:
                for version, name, path in down_queue:
                    print(f"⏪  {version} — {name} (down): {os.path.basename(path)}")
                    cur.execute("SAVEPOINT sp_reset;")
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            sql = f.read()
                        cur.execute(sql)
                        cur.execute("RELEASE SAVEPOINT sp_reset;")
                    except Exception as e:
                        # Mantém o fluxo mesmo em caso de erro pontual
                        cur.execute("ROLLBACK TO SAVEPOINT sp_reset;")
                        print(f"   ⚠️  Falha ao aplicar down de {version}_{name}: {e}")
                conn.commit()

        # Por fim, derruba schema_migrations (se existir), para forçar reapply limpo
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS schema_migrations CASCADE;")
        conn.commit()

        print("✅ RESET concluído. Você pode rodar `python db/migrate.py up` agora.")
    finally:
        conn.close()
        
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrator simples (PostgreSQL).")
    parser.add_argument("command", choices=["up", "down", "status", "reset"])
    parser.add_argument("--steps", type=int, default=1, help="quantidade para down")
    args = parser.parse_args()

    if args.command == "up":
        migrate_up()
    elif args.command == "down":
        migrate_down(steps=args.steps)
    elif args.command == "reset":
        reset()
    else:
        status()
