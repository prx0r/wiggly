#!/usr/bin/env python3
"""patala/adapters/sanskritree/adapter.py — Adapter for sanskritree old-batch import.

Reads the TypeScript seed file and converts to v2 schemas.
Source: /root/patalacheckpoints/data/atlas/sanskritreeImportSeed.ts
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.hashing import uuid7
from patala.adapters.base import SourceAdapter


SEED_FILE = Path("/root/patalacheckpoints/data/atlas/sanskritreeImportSeed.ts")


class SanskritreeAdapter(SourceAdapter):
    """Adapter for sanskritree old-batch Tantric Sanskrit corpus."""

    source_id = "sanskritree"
    adapter_version = "0.1.0"

    def __init__(self):
        self._records = self._parse_seed()

    def _parse_seed(self) -> list[dict]:
        """Parse the TypeScript seed file into Python dicts."""
        if not SEED_FILE.exists():
            return []

        content = SEED_FILE.read_text(encoding="utf-8")

        # Extract the array portion
        match = re.search(r'export const sanskritreeImportSeed.*?=\s*(\[.*?\]);', content, re.DOTALL)
        if not match:
            return []

        json_str = match.group(1)
        # Fix TypeScript-specific syntax
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)  # Quote unquoted keys
        json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)

        try:
            records = json.loads(json_str)
            return records
        except json.JSONDecodeError:
            # Fallback: extract records manually
            records = []
            for block in re.findall(r'\{[^{}]*"id":\s*"([^"]+)"[^{}]*\}', content, re.DOTALL):
                id_match = re.search(r'"id":\s*"([^"]+)"', block)
                work_match = re.search(r'"work":\s*"([^"]+)"', block)
                trad_match = re.search(r'"traditions":\s*\[([^\]]+)\]', block)

                if id_match and work_match:
                    traditions = []
                    if trad_match:
                        traditions = [t.strip().strip('"') for t in trad_match.group(1).split(",")]

                    records.append({
                        "id": id_match.group(1),
                        "work": work_match.group(1),
                        "traditions": traditions,
                    })
            return records

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        """Discover all works in the sanskritree seed."""
        items = []
        start = 0
        if cursor:
            for i, r in enumerate(self._records):
                if r["id"] == cursor:
                    start = i + 1
                    break

        for r in self._records[start:start + limit]:
            items.append({
                "resource_id": r["id"],
                "title": r["work"],
                "traditions": r.get("traditions", []),
                "url": f"sanskritree://{r['id']}",
            })

        next_cursor = self._records[start + limit]["id"] if start + limit < len(self._records) else None
        return {
            "items": items,
            "next_cursor": next_cursor,
            "source_id": self.source_id,
            "total": len(self._records),
        }

    async def fetch_metadata(self, resource: dict) -> dict:
        """Fetch metadata for a sanskritree work."""
        resource_id = resource.get("resource_id", "")
        traditions = resource.get("traditions", [])

        return {
            "id": f"PTOBS_{resource_id}",
            "provider_id": "PTPRV_sanskritree",
            "endpoint_id": "PTEP_sanskritree_seed",
            "source_resource_id": resource_id,
            "requested_uri": f"sanskritree://{resource_id}",
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_{resource_id}",
            "rights_assessment_id": "PTRTS_sanskritree",
            "run_id": None,
            "source_state": {},
            "status": "FETCHED",
            "_meta": {
                "title": resource.get("title", resource_id),
                "traditions": traditions,
                "provider": "sanskritree-old-batch",
            },
        }

    async def fetch_content(self, resource: dict) -> dict | None:
        """No content available from seed file."""
        return None

    async def normalize(self, observation: dict) -> dict:
        """Extract assertions from sanskritree observation."""
        meta = observation.get("_meta", {})
        resource_id = observation.get("source_resource_id", "")
        assertions = []
        entity_candidates = []
        external_ids = []

        # Title assertion
        if meta.get("title"):
            assertions.append({
                "id": f"PTCAS_{resource_id}_title",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_{resource_id}",
                "predicate": "TITLE",
                "value": meta["title"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.95,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Tradition assertion
        for tradition in meta.get("traditions", []):
            assertions.append({
                "id": f"PTCAS_{resource_id}_tradition_{tradition}",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_{resource_id}",
                "predicate": "TRADITION",
                "value": tradition,
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.9,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Entity candidate
        entity_candidates.append({
            "id": f"PTCND_{resource_id}",
            "candidate_type": "WORK",
            "provider_id": "PTPRV_sanskritree",
            "external_resource_id": resource_id,
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        # External ID
        external_ids.append({
            "id": f"PTEXT_{resource_id}_sanskritree",
            "entity_id": f"PTCND_{resource_id}",
            "scheme": "OTHER",
            "value": resource_id,
            "source_observation_id": observation.get("id", ""),
            "relation_confidence": 1.0,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        return {
            "observation_id": observation.get("id", ""),
            "entity_candidates": entity_candidates,
            "assertions": assertions,
            "external_ids": external_ids,
            "contained_work_candidates": [],
            "artifacts": [],
            "warnings": [],
        }


def get_adapter() -> SanskritreeAdapter:
    return SanskritreeAdapter()
