#!/usr/bin/env python3
"""patala/adapters/darshana/adapter.py — Adapter for Darshana Graph (Indic philosophy corpus).

Source: /root/patalacheckpoints/source-evidence/repos/joyboseroy__darshana-graph/corpus/

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


DARSHANA_CORPUS = Path("/root/patalacheckpoints/source-evidence/repos/joyboseroy__darshana-graph/corpus")


class DarshanaAdapter(SourceAdapter):
    """Adapter for Darshana Graph Indic philosophy corpus."""

    source_id = "darshana"
    adapter_version = "0.1.0"

    def __init__(self):
        self._verses = self._load_corpus()

    def _load_corpus(self) -> list:
        corpus_file = DARSHANA_CORPUS / "darshanas.json"
        if not corpus_file.exists():
            return []
        with open(corpus_file, encoding="utf-8") as f:
            return json.load(f)

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        items = []
        start = 0
        if cursor:
            for i, v in enumerate(self._verses):
                if v["id"] == cursor:
                    start = i + 1
                    break

        for verse in self._verses[start:start + limit]:
            items.append({
                "resource_id": verse["id"],
                "title": f'{verse.get("source", "")} {verse.get("verse", "")}',
                "tradition": verse.get("tradition", ""),
                "darshana": verse.get("darshana", ""),
                "text": verse.get("text", "")[:100],
                "sanskrit": verse.get("sanskrit", ""),
                "translator": verse.get("translator", ""),
            })

        next_cursor = self._verses[start + limit]["id"] if start + limit < len(self._verses) else None
        return {"items": items, "next_cursor": next_cursor, "source_id": self.source_id, "total": len(self._verses)}

    async def fetch_metadata(self, resource: dict) -> dict:
        return {
            "id": f"PTOBS_darshana_{resource['resource_id']}",
            "provider_id": "PTPRV_darshana",
            "endpoint_id": "PTEP_darshana_json",
            "source_resource_id": resource["resource_id"],
            "requested_uri": f"darshana://{resource['resource_id']}",
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_darshana_{resource['resource_id']}",
            "rights_assessment_id": "PTRTS_darshana",
            "run_id": None,
            "source_state": {},
            "status": "FETCHED",
            "_meta": resource,
        }

    async def fetch_content(self, resource: dict) -> dict | None:
        return None

    async def normalize(self, observation: dict) -> dict:
        meta = observation.get("_meta", {})
        resource_id = observation.get("source_resource_id", "")
        assertions = []
        entity_candidates = []
        external_ids = []

        if meta.get("title"):
            assertions.append({
                "id": f"PTCAS_darshana_{resource_id}_title",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_darshana_{resource_id}",
                "predicate": "TITLE", "value": meta["title"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.9,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        if meta.get("darshana"):
            assertions.append({
                "id": f"PTCAS_darshana_{resource_id}_tradition",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_darshana_{resource_id}",
                "predicate": "TRADITION", "value": meta["darshana"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.9,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        entity_candidates.append({
            "id": f"PTCND_darshana_{resource_id}",
            "candidate_type": "WORK",
            "provider_id": "PTPRV_darshana",
            "external_resource_id": resource_id,
            "title": meta.get("title", ""),
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        external_ids.append({
            "id": f"PTEXT_darshana_{resource_id}",
            "entity_id": f"PTCND_darshana_{resource_id}",
            "scheme": "DARSHANA", "value": resource_id,
            "source_observation_id": observation.get("id", ""),
            "relation_confidence": 1.0,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        return {
            "observation_id": observation.get("id", ""),
            "entity_candidates": entity_candidates,
            "assertions": assertions, "external_ids": external_ids,
            "contained_work_candidates": [], "artifacts": [], "warnings": [],
        }


def get_adapter() -> DarshanaAdapter:
    return DarshanaAdapter()
