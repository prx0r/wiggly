#!/usr/bin/env python3
"""patala/events.py — append-only event store with Merkle checkpoints.

Per newbuild1 §8-9, §34-37:
- Events are immutable, append-only
- Never mutate events — append corrections
- Merkle checkpoints over event batches
- Sign checkpoints, not everything

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from patala.hashing import uuid7, canonical_jcs_hash, make_digest


@dataclass
class Event:
    """An immutable event in the append-only log.

    Per newbuild1 §8: "Something happened. Not: Here is the current state of the world."
    """
    event_id: str = field(default_factory=lambda: f"PTEVT_{uuid7()}")
    event_type: str = ""
    stream_id: str | None = None
    entity_ids: list[str] = field(default_factory=list)
    schema_uri: str = "https://patala.org/schemas/v2/event-envelope.json"
    actor_id: str | None = None
    occurred_at: str | None = None
    observed_at: str | None = None
    recorded_at: str = ""
    payload: dict = field(default_factory=dict)
    payload_digest: dict = field(default_factory=dict)
    derivation_refs: list[str] = field(default_factory=list)
    run_id: str | None = None
    cursor: int = 0  # position in the log


@dataclass
class MerkleCheckpoint:
    """Merkle tree root over event batches.

    Per newbuild1 §34-35: "Many events → one independently verifiable root."
    """
    id: str = field(default_factory=lambda: f"PTCHK_{uuid7()}")
    previous_checkpoint_id: str | None = None
    first_event_cursor: int = 0
    last_event_cursor: int = 0
    event_count: int = 0
    merkle_algorithm: str = "sha512"
    merkle_root: str = ""
    generated_at: str = ""
    signatures: list[dict] = field(default_factory=list)


class EventStore:
    """Append-only event store with Merkle checkpointing.

    Per newbuild1 §33: "Do not solve distributed integrity with a global JSONL chain.
    Use batches + Merkle checkpoints."
    """

    def __init__(self, store_dir: Path | str):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.store_dir / "events.jsonl"
        self.checkpoints_file = self.store_dir / "checkpoints.jsonl"
        self._cursor = self._count_events()

    def _count_events(self) -> int:
        """Count existing events in the log."""
        if not self.events_file.exists():
            return 0
        with open(self.events_file, "r") as f:
            return sum(1 for _ in f)

    def append(self, event_type: str, entity_ids: list[str],
               payload: dict, actor_id: str | None = None,
               schema_uri: str = "https://patala.org/schemas/v2/event-envelope.json",
               occurred_at: str | None = None,
               observed_at: str | None = None,
               derivation_refs: list[str] | None = None,
               run_id: str | None = None) -> Event:
        """Append an event to the log. Never mutate existing events."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Compute payload digest using JCS canonicalization
        # Per newbuild1 §4B: "canonical JSON → RFC 8785 JCS → SHA-512"
        from patala.hashing import canonical_jcs_hash
        payload_digest = canonical_jcs_hash(payload, algorithm="sha512")

        event = Event(
            event_type=event_type,
            entity_ids=entity_ids,
            schema_uri=schema_uri,
            actor_id=actor_id,
            occurred_at=occurred_at,
            observed_at=observed_at,
            recorded_at=now,
            payload=payload,
            payload_digest=payload_digest,
            derivation_refs=derivation_refs or [],
            run_id=run_id,
            cursor=self._cursor,
        )

        # Append to JSONL (append-only, never overwrite)
        with open(self.events_file, "a") as f:
            record = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "stream_id": event.stream_id,
                "entity_ids": event.entity_ids,
                "schema_uri": event.schema_uri,
                "actor_id": event.actor_id,
                "occurred_at": event.occurred_at,
                "observed_at": event.observed_at,
                "recorded_at": event.recorded_at,
                "payload": event.payload,
                "payload_digest": event.payload_digest,
                "derivation_refs": event.derivation_refs,
                "run_id": event.run_id,
                "cursor": event.cursor,
            }
            f.write(json.dumps(record, default=str) + "\n")

        self._cursor += 1
        return event

    def get_event(self, event_id: str) -> Event | None:
        """Get an event by ID."""
        if not self.events_file.exists():
            return None
        with open(self.events_file, "r") as f:
            for line in f:
                record = json.loads(line)
                if record["event_id"] == event_id:
                    return Event(**record)
        return None

    def get_events_for_entity(self, entity_id: str) -> list[Event]:
        """Get all events for an entity."""
        events = []
        if not self.events_file.exists():
            return events
        with open(self.events_file, "r") as f:
            for line in f:
                record = json.loads(line)
                if entity_id in record.get("entity_ids", []):
                    events.append(Event(**record))
        return events

    def get_events_since(self, cursor: int, limit: int = 100) -> list[Event]:
        """Get events since a cursor position."""
        events = []
        if not self.events_file.exists():
            return events
        with open(self.events_file, "r") as f:
            for line in f:
                record = json.loads(line)
                if record["cursor"] > cursor:
                    events.append(Event(**record))
                    if len(events) >= limit:
                        break
        return events

    def build_merkle_checkpoint(self, batch_size: int = 1000) -> MerkleCheckpoint:
        """Build a Merkle checkpoint over recent events.

        Per newbuild1 §34: "Periodically: all uncheckpointed events → sort deterministically →
        event digest leaves → Merkle tree → root hash."
        """
        # Find the last checkpoint's cursor
        last_cursor = -1  # Start from -1 so first checkpoint includes cursor 0
        last_checkpoint_id = None
        if self.checkpoints_file.exists():
            with open(self.checkpoints_file, "r") as f:
                for line in f:
                    cp = json.loads(line)
                    last_cursor = cp.get("last_event_cursor", -1)
                    last_checkpoint_id = cp.get("id")

        # Get events since last checkpoint
        events = self.get_events_since(last_cursor, limit=batch_size)
        if not events:
            return MerkleCheckpoint()

        # Build Merkle tree
        leaves = []
        for event in events:
            event_bytes = json.dumps({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "entity_ids": event.entity_ids,
                "recorded_at": event.recorded_at,
                "payload": event.payload,
            }, sort_keys=True, default=str).encode()
            leaf_hash = hashlib.sha512(event_bytes).hexdigest()
            leaves.append(leaf_hash)

        # Simple Merkle tree (pair hashes up)
        while len(leaves) > 1:
            next_level = []
            for i in range(0, len(leaves), 2):
                left = leaves[i]
                right = leaves[i + 1] if i + 1 < len(leaves) else left
                combined = hashlib.sha512(f"{left}{right}".encode()).hexdigest()
                next_level.append(combined)
            leaves = next_level

        merkle_root = leaves[0] if leaves else ""

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        checkpoint = MerkleCheckpoint(
            previous_checkpoint_id=last_checkpoint_id,
            first_event_cursor=last_cursor + 1,
            last_event_cursor=events[-1].cursor,
            event_count=len(events),
            merkle_root=merkle_root,
            generated_at=now,
        )

        # Append checkpoint to JSONL
        with open(self.checkpoints_file, "a") as f:
            f.write(json.dumps({
                "id": checkpoint.id,
                "previous_checkpoint_id": checkpoint.previous_checkpoint_id,
                "first_event_cursor": checkpoint.first_event_cursor,
                "last_event_cursor": checkpoint.last_event_cursor,
                "event_count": checkpoint.event_count,
                "merkle_algorithm": checkpoint.merkle_algorithm,
                "merkle_root": checkpoint.merkle_root,
                "generated_at": checkpoint.generated_at,
                "signatures": checkpoint.signatures,
            }, default=str) + "\n")

        return checkpoint

    def verify_checkpoint(self, checkpoint_id: str) -> bool:
        """Verify a checkpoint's Merkle root is correct."""
        if not self.checkpoints_file.exists():
            return False

        # Find the checkpoint
        checkpoint = None
        with open(self.checkpoints_file, "r") as f:
            for line in f:
                cp = json.loads(line)
                if cp["id"] == checkpoint_id:
                    checkpoint = cp
                    break

        if not checkpoint:
            return False

        # Rebuild the Merkle tree for the events in this checkpoint
        events = self.get_events_since(
            checkpoint["first_event_cursor"] - 1,
            limit=checkpoint["event_count"]
        )

        leaves = []
        for event in events:
            event_bytes = json.dumps({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "entity_ids": event.entity_ids,
                "recorded_at": event.recorded_at,
                "payload": event.payload,
            }, sort_keys=True, default=str).encode()
            leaf_hash = hashlib.sha512(event_bytes).hexdigest()
            leaves.append(leaf_hash)

        # Rebuild Merkle tree
        while len(leaves) > 1:
            next_level = []
            for i in range(0, len(leaves), 2):
                left = leaves[i]
                right = leaves[i + 1] if i + 1 < len(leaves) else left
                combined = hashlib.sha512(f"{left}{right}".encode()).hexdigest()
                next_level.append(combined)
            leaves = next_level

        return leaves[0] == checkpoint["merkle_root"] if leaves else False

    @property
    def cursor(self) -> int:
        return self._cursor


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir)

        print("=== Append Events ===")
        for i in range(5):
            event = store.append(
                event_type="EntityCreated",
                entity_ids=[f"PTW_{i:04d}"],
                payload={"title": f"Work {i}", "author": f"Author {i}"},
            )
            print(f"  {event.event_id} cursor={event.cursor}")

        print(f"\nTotal events: {store.cursor}")

        print("\n=== Get Events for Entity ===")
        events = store.get_events_for_entity("PTW_0001")
        print(f"  Events for PTW_0001: {len(events)}")

        print("\n=== Build Merkle Checkpoint ===")
        checkpoint = store.build_merkle_checkpoint()
        print(f"  Checkpoint: {checkpoint.id}")
        print(f"  Events: {checkpoint.event_count}")
        print(f"  Merkle root: {checkpoint.merkle_root[:32]}...")

        print("\n=== Verify Checkpoint ===")
        valid = store.verify_checkpoint(checkpoint.id)
        print(f"  Valid: {valid}")
