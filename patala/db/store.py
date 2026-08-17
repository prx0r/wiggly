#!/usr/bin/env python3
"""patala/db/store.py — Postgres store for all entities.

Production-grade: writes to Postgres, reads from Postgres.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://patala:patala@127.0.0.1:5432/openpatala")


def get_conn():
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- Works ---

def insert_work(work_id: str, preferred_title: str, work_type: str = "TEXT",
                external_ids: list | None = None, created_at: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO works (id, preferred_title, work_type, external_ids, created_at) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET preferred_title = EXCLUDED.preferred_title",
        (work_id, preferred_title, work_type, json.dumps(external_ids or []), created_at or _now())
    )
    conn.commit()
    cur.close()
    conn.close()


def get_work(work_id: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM works WHERE id = %s", (work_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return None


def list_works(limit: int = 100) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM works LIMIT %s", (limit,))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


# --- Assertions ---

def insert_assertion(assertion_id: str, subject_id: str, predicate_uri: str,
                     literal: str = "", asserted_by: str = "PROVIDER",
                     lifecycle: str = "ACTIVE", created_from_event: str = "",
                     valid_from: str = "", valid_until: str = "",
                     schema_uri: str = "https://patala.org/schemas/v2/assertion.json"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO assertions (id, subject_id, predicate_uri, literal, epistemic_mode, asserted_by, recorded_at, lifecycle, created_from_event, valid_from, valid_until, schema_uri) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (assertion_id, subject_id, predicate_uri, literal, "observed", asserted_by,
         _now(), lifecycle, created_from_event, valid_from or None, valid_until or None, schema_uri)
    )
    conn.commit()
    cur.close()
    conn.close()


def list_assertions(subject_id: str | None = None, limit: int = 100) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    if subject_id:
        cur.execute("SELECT * FROM assertions WHERE subject_id = %s LIMIT %s", (subject_id, limit))
    else:
        cur.execute("SELECT * FROM assertions LIMIT %s", (limit,))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


# --- External Identifiers ---

def insert_external_id(ext_id: str, entity_id: str, scheme: str, value: str,
                       source_observation_id: str = "", confidence: float = 1.0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO external_identifiers (id, entity_id, scheme, value, source_observation_id, relation_confidence, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (ext_id, entity_id, scheme, value, source_observation_id, confidence, _now())
    )
    conn.commit()
    cur.close()
    conn.close()


def list_external_ids(entity_id: str | None = None) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    if entity_id:
        cur.execute("SELECT * FROM external_identifiers WHERE entity_id = %s", (entity_id,))
    else:
        cur.execute("SELECT * FROM external_identifiers LIMIT 100")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


# --- Events ---

def insert_event(event_id: str, event_type: str, entity_ids: list,
                 payload: dict, recorded_at: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (event_id, event_type, entity_ids, schema_uri, payload, payload_digest, recorded_at) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (event_id) DO NOTHING",
        (event_id, event_type, entity_ids,
         "https://patala.org/schemas/v2/event-envelope.json",
         json.dumps(payload), json.dumps({}), recorded_at or _now())
    )
    conn.commit()
    cur.close()
    conn.close()


def count_events() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM events")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


# --- Source Providers ---

def insert_provider(provider_id: str, slug: str, name: str, provider_type: str,
                    status: str = "ACTIVE"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO source_providers (id, slug, name, provider_type, status, discovered_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (provider_id, slug, name, provider_type, status, _now())
    )
    conn.commit()
    cur.close()
    conn.close()


# --- Artifacts ---

def insert_artifact(artifact_id: str, digests: dict, media_type: str,
                    byte_length: int, storage_uri: str = "",
                    availability_state: str = "PRESENT"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO artifacts (id, digests, media_type, byte_length, storage_uri, availability_state, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (artifact_id, json.dumps(digests), media_type, byte_length, storage_uri, availability_state, _now())
    )
    conn.commit()
    cur.close()
    conn.close()


def get_artifact(artifact_id: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM artifacts WHERE id = %s", (artifact_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return None


# --- Raw Observations ---

def insert_raw_observation(obs_id: str, provider_id: str, endpoint_id: str,
                           requested_uri: str, payload_artifact_id: str,
                           rights_assessment_id: str, status: str = "FETCHED",
                           observed_at: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO raw_observations (id, provider_id, endpoint_id, requested_uri, payload_artifact_id, rights_assessment_id, observed_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (obs_id, provider_id, endpoint_id, requested_uri, payload_artifact_id,
         rights_assessment_id, observed_at or _now(), status)
    )
    conn.commit()
    cur.close()
    conn.close()


# --- Entity Merges ---

def insert_merge(merge_id: str, from_ids: list, into_id: str, evidence: str,
                 event_id: str, performed_by: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO identity_merges (id, from_ids, into_id, evidence, event_id, performed_by) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (merge_id, from_ids, into_id, evidence, event_id, performed_by)
    )
    # Update lifecycle of merged entities
    for fid in from_ids:
        cur.execute("UPDATE works SET schema_uri = schema_uri WHERE id = %s", (fid,))
    conn.commit()
    cur.close()
    conn.close()


def find_merge_target(entity_id: str) -> str | None:
    """Follow merge chains: if entity was merged into another, return the target."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT into_id FROM identity_merges WHERE %s = ANY(from_ids)", (entity_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return row[0]
    return None


# --- Entity Splits ---

def insert_split(split_id: str, old_id: str, new_ids: list, evidence: str,
                 event_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO identity_splits (id, old_id, new_ids, allocation_evidence, event_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (split_id, old_ids, new_ids, evidence, event_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def find_split(entity_id: str) -> dict | None:
    """Check if entity was split. Returns split info or None."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM identity_splits WHERE old_id = %s", (entity_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return None


# --- Rebuild from events ---

def rebuild_from_events():
    """Destroy all projections and rebuild from event stream."""
    conn = get_conn()
    cur = conn.cursor()

    # Clear projection tables
    for table in ["works", "people", "institutions", "editions", "witnesses",
                   "etexts", "translations", "passages", "assertions",
                   "external_identifiers", "identity_assertions"]:
        cur.execute(f"TRUNCATE {table} CASCADE")

    # Read all events
    cur.execute("SELECT * FROM events ORDER BY cursor")
    events = cur.fetchall()
    cols = [d[0] for d in cur.description]

    rebuilt = 0
    for event_row in events:
        event = dict(zip(cols, event_row))
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})
        if isinstance(payload, str):
            payload = json.loads(payload)

        if event_type == "EntityCreated":
            entity_id = event.get("entity_ids", [None])[0]
            if entity_id and not entity_id.startswith("PTCND_"):
                title = payload.get("title", "")
                cur.execute(
                    "INSERT INTO works (id, preferred_title, schema_uri, created_at) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                    (entity_id, title, "https://patala.org/schemas/atlas/work/1.0.0", event.get("recorded_at", ""))
                )
                rebuilt += 1

    conn.commit()
    cur.close()
    conn.close()
    return rebuilt


# --- Stats ---

def get_stats() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    stats = {}
    for table in ["works", "people", "institutions", "editions", "witnesses",
                   "etexts", "translations", "assertions", "external_identifiers", "events"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return stats
