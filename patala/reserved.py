#!/usr/bin/env python3
"""patala/schema_registry/reserved.py — Reserved fields tracking.

Per newbuild1 §15: "Never reuse a retired field semantically.
Protocol Buffers has learned this the painful way: removed field numbers
should be reserved and not later reused for different meanings."

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patala.hashing import uuid7
from patala.db import store


# Reserved fields per schema family
RESERVED_FIELDS = {
    "atlas/work": [
        "author",  # Deprecated: use assertion-based authorship
        "date",  # Deprecated: use assertion-based dating
        "school",  # Deprecated: use assertion-based tradition
    ],
    "atlas/edition": [
        "edition_type",  # Deprecated: translations are separate entities
    ],
    "source/observation": [
        "payload_hash",  # Deprecated: use artifact reference
    ],
}


def reserve_field(schema_family: str, field_name: str, reason: str = ""):
    """Reserve a field name within a schema family.

    Per newbuild1 §15: "If Work.author dies: reserve author within that schema family.
    Don't bring it back in 2031 meaning 'primary modern editor'."
    """
    conn = store.get_conn()
    cur = conn.cursor()

    # Store in schema_registry as a reserved field entry
    reservation_id = f"PTRSV_{uuid7().replace(chr(45), '')[:16]}"
    cur.execute(
        '''INSERT INTO schema_registry
        (uri, family, version, schema_dialect, artifact_id, digest_set, published_at, supersedes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (uri) DO NOTHING''',
        (f"reserved://{schema_family}/{field_name}", schema_family, "0.0.0",
         "reservation", None, json.dumps({"reserved": True, "reason": reason}),
         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), None)
    )
    conn.commit()
    cur.close()
    conn.close()


def is_reserved(schema_family: str, field_name: str) -> bool:
    """Check if a field is reserved (cannot be reused)."""
    key = f"reserved://{schema_family}/{field_name}"
    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM schema_registry WHERE uri = %s", (key,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count > 0


def list_reserved(schema_family: str) -> list[str]:
    """List all reserved fields for a schema family."""
    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT uri FROM schema_registry WHERE family = %s AND version = '0.0.0'",
        (schema_family,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    reserved = []
    for row in rows:
        uri = row[0]
        if uri.startswith("reserved://"):
            field = uri.split("/")[-1]
            reserved.append(field)
    return reserved
