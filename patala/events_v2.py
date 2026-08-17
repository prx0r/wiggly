#!/usr/bin/env python3
"""patala/events_v2.py — Postgres-only canonical event ledger.

Per 0.6A: "Make Postgres the sole canonical live event ledger.
JSONL becomes export/backup/snapshot distribution only."

Per newbuild1 §9: "Never mutate events."

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patala.hashing import uuid7, canonical_jcs_hash
from patala.db import store


class CanonicalEventStore:
    """Postgres-only canonical event ledger.

    Per 0.6A:
    - One Event ID
    - One cursor (DB-generated)
    - One payload digest
    - One schema URI
    - No JSONL writer
    """

    def append(self, event_type: str, entity_ids: list,
               payload: dict, actor_id: str | None = None,
               schema_uri: str = "https://patala.org/schemas/v2/event-envelope.json",
               occurred_at: str | None = None,
               observed_at: str | None = None,
               derivation_refs: list[str] | None = None,
               run_id: str | None = None) -> dict:
        """Append event to Postgres (sole canonical ledger)."""
        event_id = f"PTEVT_{uuid7().replace('-', '')[:16]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # JCS payload digest
        from patala.hashing import canonical_jcs_hash
        payload_digest = canonical_jcs_hash(payload, algorithm="sha512")

        conn = store.get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO events (event_id, event_type, entity_ids, schema_uri,
                actor_id, occurred_at, observed_at, recorded_at, payload,
                payload_digest, derivation_refs, run_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (event_id, event_type, entity_ids, schema_uri,
              actor_id, occurred_at, observed_at, now,
              json.dumps(payload), json.dumps(payload_digest),
              derivation_refs or [], run_id))
        conn.commit()
        cur.close()
        conn.close()

        return {"event_id": event_id, "recorded_at": now}

    def get_events_since(self, cursor: int, limit: int = 100) -> list[dict]:
        """Read events from Postgres (sole canonical source)."""
        conn = store.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM events WHERE cursor > %s ORDER BY cursor LIMIT %s", (cursor, limit))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close()
        conn.close()
        return [dict(zip(cols, r)) for r in rows]

    def count(self) -> int:
        conn = store.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count

    def max_cursor(self) -> int:
        conn = store.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(cursor), 0) FROM events")
        max_c = cur.fetchone()[0]
        cur.close()
        conn.close()
        return max_c
