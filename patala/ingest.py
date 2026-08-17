#!/usr/bin/env python3
"""patala/ingest.py — The ingestion pipeline (Postgres-backed).

Per newbuildmainspec §3: SOURCE → RAW OBSERVATION → CANDIDATE ASSERTION → IDENTITY RESOLUTION → ENTITY

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patala.hashing import uuid7, make_digest_set, raw_byte_hash
from patala.entities import Work
from patala.resolver import Resolver
from patala.events_v2 import CanonicalEventStore as EventStore
from patala.completeness import CompletenessCompiler
from patala.adapters.base import SourceAdapter
from patala.db import store


class IngestionPipeline:
    """End-to-end ingestion: discover → fetch → extract → resolve → store."""

    def __init__(self, adapter: SourceAdapter, event_store: EventStore,
                 resolver: Resolver, completeness: CompletenessCompiler):
        self.adapter = adapter
        self.event_store = event_store
        self.resolver = resolver
        self.completeness = completeness
        self.stats = {
            "discovered": 0, "fetched": 0, "extracted": 0,
            "resolved": 0, "created": 0, "events": 0,
            "assertions_written": 0, "ext_ids_written": 0,
        }

    async def run(self, limit: int = 10, cursor: str | None = None) -> dict:
        print(f"{'='*60}")
        print(f"INGESTION PIPELINE — {self.adapter.source_id}")
        print(f"{'='*60}")

        # Step 1: Discover
        print(f"\n[1/5] DISCOVER")
        discovery = await self.adapter.discover(cursor=cursor, limit=limit)
        items = discovery["items"]
        self.stats["discovered"] = len(items)
        print(f"  Found {len(items)} items (total: {discovery.get('total', '?')})")

        # Step 2: Fetch metadata
        print(f"\n[2/5] FETCH")
        observations = []
        for i, item in enumerate(items):
            obs = await self.adapter.fetch_metadata(item)
            observations.append(obs)
            self.stats["fetched"] += 1
            self.event_store.append(
                event_type="RawObservationRecorded",
                entity_ids=[obs.get("id", "")],
                payload={"resource_id": item.get("resource_id")},
            )
            self.stats["events"] += 1
            print(f"  [{i+1}/{len(items)}] {item.get('title', item.get('resource_id', '?'))[:50]}")

        # Step 3: Extract assertions (store bundles with candidates)
        print(f"\n[3/5] EXTRACT")
        candidates_with_bundles = []
        all_assertions = []
        all_ext_ids = []

        for obs in observations:
            bundle = await self.adapter.normalize(obs)
            all_assertions.extend(bundle["assertions"])
            all_ext_ids.extend(bundle["external_ids"])
            self.stats["extracted"] += len(bundle["assertions"])

            # Store bundle with each candidate for later writing
            for candidate in bundle["entity_candidates"]:
                candidates_with_bundles.append({
                    "candidate": candidate,
                    "assertions": bundle["assertions"],
                    "ext_ids": bundle["external_ids"],
                })

        print(f"  {len(all_assertions)} assertions, {len(candidates_with_bundles)} candidates, {len(all_ext_ids)} external IDs")

        # Step 4: Resolve identities and write ALL data to Postgres
        print(f"\n[4/5] RESOLVE + WRITE")
        resolved = {}
        for item in candidates_with_bundles:
            candidate = item["candidate"]
            proposal = self.resolver.resolve([candidate])
            self.stats["resolved"] += 1

            if proposal.proposed_entity_id:
                entity_id = proposal.proposed_entity_id
            else:
                # New entity
                w = Work(preferred_title=candidate.get("title", candidate["id"]))
                entity_id = w.id
                self.resolver.register_entity(w.id, {"title": w.preferred_title})
                self.stats["created"] += 1

                # Write Work to Postgres
                store.insert_work(w.id, w.preferred_title, w.work_type,
                                  candidate.get("external_ids", []))

            resolved[candidate["id"]] = entity_id

            # Write ALL assertions for this candidate to Postgres
            for assertion in item["assertions"]:
                store.insert_assertion(
                    assertion["id"],
                    entity_id,  # Map candidate → entity
                    assertion.get("predicate", ""),
                    assertion.get("value", ""),
                    asserted_by="PROVIDER",
                    lifecycle="ACTIVE"
                )
                self.stats["assertions_written"] += 1

            # Write ALL external IDs for this candidate to Postgres
            for ext_id in item["ext_ids"]:
                store.insert_external_id(
                    ext_id["id"],
                    ext_id.get("entity_id", entity_id),
                    ext_id.get("scheme", ""),
                    ext_id.get("value", ""),
                    ext_id.get("source_observation_id", ""),
                    ext_id.get("relation_confidence", 1.0)
                )
                self.stats["ext_ids_written"] += 1

            # Record entity creation event
            self.event_store.append(
                event_type="EntityCreated",
                entity_ids=[entity_id],
                payload={"title": candidate.get("title", "")},
            )
            store.insert_event(
                f"PTEVT_{uuid7()}", "EntityCreated",
                [entity_id], {"title": candidate.get("title", "")}
            )
            self.stats["events"] += 1

        unique_entities = len(set(resolved.values()))
        print(f"  {unique_entities} unique entities ({self.stats['created']} new)")
        print(f"  {self.stats['assertions_written']} assertions written to Postgres")
        print(f"  {self.stats['ext_ids_written']} external IDs written to Postgres")

        # Step 5: Compile completeness
        print(f"\n[5/5] COMPLETE")
        stats = store.get_stats()
        print(f"  Postgres: {stats['works']} works, {stats['assertions']} assertions, {stats['external_identifiers']} ext_ids")

        # Build checkpoint
        cp = self.event_store.build_merkle_checkpoint()
        valid = self.event_store.verify_checkpoint(cp.id)
        print(f"  Checkpoint: {cp.id} (valid={valid})")

        print(f"\n{'='*60}")
        print(f"INGESTION COMPLETE")
        print(f"  Created: {self.stats['created']}")
        print(f"  Assertions written: {self.stats['assertions_written']}")
        print(f"  Ext IDs written: {self.stats['ext_ids_written']}")
        print(f"  Events: {self.stats['events']}")
        print(f"{'='*60}")

        return self.stats
