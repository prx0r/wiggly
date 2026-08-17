#!/usr/bin/env python3
"""patala/factory/availability.py — Translation availability compiler (Postgres-backed).

Compiles translation availability from the OpenPāṭala database.
Per newbuildmainspec §24: "TranslationAvailability is a projection, not primary truth."

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.db import store


def compile_availability(work_id: str) -> dict:
    """Compile translation availability for a work from Postgres data.

    Returns TranslationAvailability-shaped dict.
    """
    conn = store.get_conn()
    cur = conn.cursor()

    # Get work
    cur.execute("SELECT * FROM works WHERE id = %s", (work_id,))
    work_row = cur.fetchone()
    if not work_row:
        cur.close()
        conn.close()
        return {"work_id": work_id, "state": "NOT_FOUND"}

    # Get translations
    cur.execute("SELECT * FROM translations WHERE work_id = %s", (work_id,))
    translations = cur.fetchall()
    trans_cols = [d[0] for d in cur.description] if translations else []
    trans_list = [dict(zip(trans_cols, t)) for t in translations]

    # Get external IDs
    cur.execute("SELECT * FROM external_identifiers WHERE entity_id = %s", (work_id,))
    ext_ids = cur.fetchall()
    ext_cols = [d[0] for d in cur.description] if ext_ids else []
    ext_list = [dict(zip(ext_cols, e)) for e in ext_ids]

    cur.close()
    conn.close()

    # Compute state
    if trans_list:
        has_full = any(t.get("completeness") == "FULL" for t in trans_list)
        has_partial = any(t.get("completeness") == "PARTIAL" for t in trans_list)
        state = "FULL" if has_full else "PARTIAL" if has_partial else "EXISTING"
    else:
        state = "NONE_KNOWN"

    # Check for English translations
    english_translations = [t for t in trans_list if t.get("target_language") == "eng"]
    english_state = "FULL" if any(t.get("completeness") == "FULL" for t in english_translations) else \
                    "PARTIAL" if english_translations else "NONE_KNOWN"

    # Check for GRETIL/OpenAlex links (bibliography)
    has_bibliography = any(e.get("scheme") in ("GRETIL", "DOI", "OPENALEX") for e in ext_list)

    return {
        "work_id": work_id,
        "state": state,
        "translations": [{"id": t["id"], "language": t.get("target_language"),
                          "completeness": t.get("completeness")} for t in trans_list],
        "english_state": english_state,
        "translation_count": len(trans_list),
        "has_bibliography": has_bibliography,
        "external_id_count": len(ext_list),
    }


def compile_all_availability() -> list[dict]:
    """Compile translation availability for all works."""
    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM works")
    work_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    results = []
    for wid in work_ids:
        results.append(compile_availability(wid))

    return results


def get_frontier(limit: int = 20) -> list[dict]:
    """List works needing translations (the frontier)."""
    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT w.id, w.preferred_title
        FROM works w
        LEFT JOIN translations t ON t.work_id = w.id
        WHERE t.id IS NULL
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{"work_id": row[0], "title": row[1], "translation_state": "NONE_KNOWN",
             "factory_eligible": True} for row in rows]
