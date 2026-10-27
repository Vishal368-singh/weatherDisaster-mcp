
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

required = [
    "PGHOST",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
]

missing = [key for key in required if not os.getenv(key)]

if missing:
    raise RuntimeError(
        f"Missing environment variables: {', '.join(missing)}"
    )

try:
    with psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode=os.getenv("PGSSLMODE", "prefer"),
        connect_timeout=10,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    current_database(),
                    current_user,
                    to_regclass(
                        'weatherdata.district_wise_7dayfc_severity'
                    )
            """)

            database, username, table = cur.fetchone()

            print("PostgreSQL connection successful.")
            print(f"Database: {database}")
            print(f"User: {username}")
            print(f"Target table: {table}")

            if table is None:
                print("WARNING: Target table was not found.")

except psycopg.Error as exc:
    print(f"PostgreSQL connection failed: {exc}")
