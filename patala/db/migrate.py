#!/usr/bin/env python3
"""patala/db/migrate.py — run SQL migrations."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.db.connection import get_connection


def run_migrations():
    """Run all SQL migrations in order."""
    conn = get_connection()
    cur = conn.cursor()

    migrations_dir = Path(__file__).resolve().parents[2] / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    for sql_file in sql_files:
        print(f"Running {sql_file.name}...")
        sql = sql_file.read_text()
        try:
            cur.execute(sql)
            conn.commit()
            print(f"  OK")
        except Exception as e:
            conn.rollback()
            print(f"  ERROR: {e}")
            sys.exit(1)

    print(f"\nAll {len(sql_files)} migrations complete.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    run_migrations()
