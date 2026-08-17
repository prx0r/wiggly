#!/usr/bin/env python3
"""patala/adapters/pandit/adapter.py — Adapter for PANDiT (Prosopographical Database of Indic Texts).

PANDiT provides curated metadata for premodern South Asian works, people, and manuscripts.
Source: /root/patalacheckpoints/source-evidence/repos/tylergneill__panditya/data/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.hashing import uuid7
from patala.adapters.base import SourceAdapter


PANDIT_DATA = Path("/root/patalacheckpoints/source-evidence/repos/tylergneill__panditya/data")


class PanditAdapter(SourceAdapter):
    """Adapter for PANDiT prosopographical database."""

    source_id = "pandit"
    adapter_version = "0.1.0"

    def __init__(self):
        self._entities = self._load_entities()

    def _load_entities(self) -> dict:
        """Load PANDiT entities from JSON."""
        entities_file = PANDIT_DATA / "2025-11-07-entities.json"
        if not entities_file.exists():
            return {}
        with open(entities_file, encoding="utf-8") as f:
            return json.load(f)

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        """Discover PANDiT entities (works and authors)."""
        items = []
        keys = list(self._entities.keys())

        start = 0
        if cursor:
            for i, k in enumerate(keys):
                if k == cursor:
                    start = i + 1
                    break

        for key in keys[start:start + limit]:
            entity = self._entities[key]
            items.append({
                "resource_id": key,
                "title": entity.get("name", ""),
                "entity_type": entity.get("type", ""),
                "aka": entity.get("aka", []),
                "discipline": entity.get("discipline", ""),
                "url": f"https://pandit.org/entity/{key}",
            })

        next_cursor = keys[start + limit] if start + limit < len(keys) else None
        return {
            "items": items,
            "next_cursor": next_cursor,
            "source_id": self.source_id,
            "total": len(self._entities),
        }

    async def fetch_metadata(self, resource: dict) -> dict:
        """Fetch metadata for a PANDiT entity."""
        return {
            "id": f"PTOBS_pandit_{resource['resource_id']}",
            "provider_id": "PTPRV_pandit",
            "endpoint_id": "PTEP_pandit_json",
            "source_resource_id": resource["resource_id"],
            "requested_uri": resource.get("url", ""),
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_pandit_{resource['resource_id']}",
            "rights_assessment_id": "PTRTS_pandit",
            "run_id": None,
            "source_state": {},
            "status": "FETCHED",
            "_meta": {
                "title": resource.get("title", ""),
                "entity_type": resource.get("entity_type", ""),
                "aka": resource.get("aka", []),
                "discipline": resource.get("discipline", ""),
                "pandit_id": resource["resource_id"],
            },
        }

    async def fetch_content(self, resource: dict) -> dict | None:
        """No content to fetch — PANDiT is metadata-only."""
        return None

    async def normalize(self, observation: dict) -> dict:
        """Extract assertions from PANDiT observation."""
        meta = observation.get("_meta", {})
        resource_id = observation.get("source_resource_id", "")
        entity_type = meta.get("entity_type", "")
        assertions = []
        entity_candidates = []
        external_ids = []

        # Title/name assertion
        if meta.get("title"):
            assertions.append({
                "id": f"PTCAS_pandit_{resource_id}_title",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_pandit_{resource_id}",
                "predicate": "TITLE",
                "value": meta["title"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.95,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Alternative names
        aka = meta.get("aka", "")
        if aka:
            # aka is a string, not a list
            assertions.append({
                "id": f"PTCAS_pandit_{resource_id}_aka_{hash(aka) % 10000}",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_pandit_{resource_id}",
                "predicate": "TITLE",
                "value": aka,
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.8,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Entity candidate
        candidate_type = "WORK" if entity_type == "work" else "PERSON"
        entity_candidates.append({
            "id": f"PTCND_pandit_{resource_id}",
            "candidate_type": candidate_type,
            "provider_id": "PTPRV_pandit",
            "external_resource_id": resource_id,
            "title": meta.get("title", ""),
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        # External ID
        external_ids.append({
            "id": f"PTEXT_pandit_{resource_id}",
            "entity_id": f"PTCND_pandit_{resource_id}",
            "scheme": "PANDIT",
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


def get_adapter() -> PanditAdapter:
    return PanditAdapter()
