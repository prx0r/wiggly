#!/usr/bin/env python3
"""patala/work_coverage.py — WorkCoverage (replacing WorkCompleteness).

Per pathway §12: "Replace WorkCompleteness with WorkCoverage."
Coverage is computed from canonical state, not hardcoded.

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patala.db import store


def compute_coverage(work_id: str) -> dict:
    """Compute WorkCoverage from canonical state in Postgres.

    Per pathway §12: "WorkCoverage should be computed from canonical state."
    """
    conn = store.get_conn()
    cur = conn.cursor()

    # Get work
    cur.execute("SELECT * FROM works WHERE id = %s", (work_id,))
    work_row = cur.fetchone()
    if not work_row:
        cur.close()
        conn.close()
        return {"work_id": work_id, "status": "NOT_FOUND"}

    work = dict(zip([d[0] for d in cur.description], work_row))

    # Count related entities
    cur.execute("SELECT COUNT(*) FROM assertions WHERE subject_id = %s", (work_id,))
    assertion_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM external_identifiers WHERE entity_id = %s", (work_id,))
    ext_id_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM editions WHERE work_id = %s", (work_id,))
    edition_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM translations WHERE work_id = %s", (work_id,))
    translation_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM witnesses WHERE work_id = %s", (work_id,))
    witness_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM etexts WHERE work_id = %s", (work_id,))
    etext_count = cur.fetchone()[0]

    # Compute coverage dimensions
    identity = "RESOLVED" if work.get("preferred_title") else "UNRESOLVED"
    source = "ETEXT" if etext_count > 0 else ("CATALOG" if edition_count > 0 else "NONE")
    translation = "EXISTING" if translation_count > 0 else "NONE_KNOWN"
    bibliography = "COMPLETE" if ext_id_count > 0 else "NONE"

    cur.close()
    conn.close()

    return {
        "work_id": work_id,
        "identity": identity,
        "source": source,
        "translation": translation,
        "alignment": "NONE",
        "evaluation": "NONE",
        "bibliography": bibliography,
        "assertion_count": assertion_count,
        "ext_id_count": ext_id_count,
        "edition_count": edition_count,
        "translation_count": translation_count,
        "witness_count": witness_count,
        "etext_count": etext_count,
    }


def get_coverage_stats() -> dict:
    """Get overall coverage statistics."""
    conn = store.get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM works")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM works WHERE preferred_title != ''")
    resolved = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT work_id) FROM etexts")
    with_text = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT work_id) FROM translations")
    with_translation = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT entity_id) FROM external_identifiers")
    with_bibliography = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "total": total,
        "resolved": resolved,
        "with_text": with_text,
        "with_translation": with_translation,
        "with_bibliography": with_bibliography,
        "resolution_rate": round(resolved / total * 100, 1) if total else 0,
        "text_rate": round(with_text / total * 100, 1) if total else 0,
        "translation_rate": round(with_translation / total * 100, 1) if total else 0,
        "bibliography_rate": round(with_bibliography / total * 100, 1) if total else 0,
    }
