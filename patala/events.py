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

    def build_merkle_checkpoint(self):
        """Build a Merkle checkpoint over all events in cursor order."""
        import hashlib
        from types import SimpleNamespace

        conn = store.get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT event_id, cursor, payload_digest FROM events ORDER BY cursor"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            # Empty ledger — synthetic root
            leaf_hashes = []
            root = hashlib.sha256(b"empty-ledger").hexdigest()
        else:
            leaf_hashes = []
            for event_id, cursor, payload_digest in rows:
                # Each leaf = hash(event_id || cursor || payload_digest)
                if isinstance(payload_digest, dict):
                    digest_val = payload_digest.get("value", "")
                else:
                    digest_val = str(payload_digest)
                leaf_input = f"{event_id}:{cursor}:{digest_val}".encode()
                leaf_hashes.append(hashlib.sha256(leaf_input).hexdigest())

            # Build Merkle root by pairwise hashing up the tree
            level = leaf_hashes
            while len(level) > 1:
                next_level = []
                for i in range(0, len(level), 2):
                    left = level[i]
                    right = level[i + 1] if i + 1 < len(level) else left
                    combined = hashlib.sha256(
                        (left + right).encode()
                    ).hexdigest()
                    next_level.append(combined)
                level = next_level
            root = level[0]

        # Get previous checkpoint
        conn2 = store.get_conn()
        cur2 = conn2.cursor()
        try:
            cur2.execute(
                "SELECT id FROM ledger_checkpoints ORDER BY first_event_cursor DESC LIMIT 1"
            )
            prev_row = cur2.fetchone()
            prev_id = prev_row[0] if prev_row else None
        finally:
            cur2.close()
            conn2.close()

        checkpoint_id = f"PTCP_{uuid7().replace('-', '')[:16]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        first_cursor = rows[0][1] if rows else 0
        last_cursor = rows[-1][1] if rows else 0
        event_count = len(rows)

        merkle_obj = {"root": root, "leaf_count": len(leaf_hashes)}

        conn3 = store.get_conn()
        cur3 = conn3.cursor()
        cur3.execute(
            """INSERT INTO ledger_checkpoints
               (id, previous_checkpoint_id, first_event_cursor, last_event_cursor,
                event_count, merkle, generated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (checkpoint_id, prev_id, first_cursor, last_cursor,
             event_count, json.dumps(merkle_obj), now),
        )
        conn3.commit()
        cur3.close()
        conn3.close()

        return SimpleNamespace(id=checkpoint_id, merkle=merkle_obj, generated_at=now)

    def verify_checkpoint(self, checkpoint_id: str) -> bool:
        """Verify a checkpoint: recompute Merkle root from events and compare."""
        import hashlib

        conn = store.get_conn()
        cur = conn.cursor()

        # Load checkpoint
        cur.execute(
            "SELECT first_event_cursor, last_event_cursor, merkle FROM ledger_checkpoints WHERE id = %s",
            (checkpoint_id,),
        )
        cp_row = cur.fetchone()
        if not cp_row:
            cur.close()
            conn.close()
            return False
        first_c, last_c, merkle = cp_row
        if isinstance(merkle, str):
            merkle = json.loads(merkle)
        stored_root = merkle.get("root", "")

        # Recompute from events in range
        cur.execute(
            "SELECT event_id, cursor, payload_digest FROM events WHERE cursor >= %s AND cursor <= %s ORDER BY cursor",
            (first_c, last_c),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return stored_root == hashlib.sha256(b"empty-ledger").hexdigest()

        leaf_hashes = []
        for event_id, cursor, payload_digest in rows:
            if isinstance(payload_digest, dict):
                digest_val = payload_digest.get("value", "")
            else:
                digest_val = str(payload_digest)
            leaf_input = f"{event_id}:{cursor}:{digest_val}".encode()
            leaf_hashes.append(hashlib.sha256(leaf_input).hexdigest())

        level = leaf_hashes
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                next_level.append(combined)
            level = next_level

        return level[0] == stored_root
