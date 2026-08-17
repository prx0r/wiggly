#!/usr/bin/env python3
"""patala/adapters/ror/adapter.py — Adapter for ROR (Research Organization Registry).

ROR provides persistent institution identifiers via REST API.
API: https://api.ror.org/organizations

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.hashing import uuid7
from patala.adapters.base import SourceAdapter


ROR_API = "https://api.ror.org/organizations"


class RorAdapter(SourceAdapter):
    """Adapter for ROR institution identity."""

    source_id = "ror"
    adapter_version = "0.1.0"

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        params = {"query": "sanskrit", "per_page": str(limit)}
        if cursor:
            params["page"] = cursor
        url = f"{ROR_API}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "openpatala/1.0"
            })
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            return {"items": [], "next_cursor": None, "source_id": self.source_id, "total": 0, "error": str(e)}

        items = []
        for org in data.get("organizations", []):
            items.append({
                "resource_id": org.get("id", "").split("/")[-1],
                "name": org.get("name", ""),
                "country": org.get("country", {}).get("name", ""),
                "types": org.get("types", []),
                "url": org.get("id", ""),
            })

        total = data.get("meta", {}).get("total", 0)
        next_page = data.get("meta", {}).get("next_page")
        next_cursor = "2" if next_page else None
        return {"items": items, "next_cursor": next_cursor, "source_id": self.source_id, "total": total}

    async def fetch_metadata(self, resource: dict) -> dict:
        return {
            "id": f"PTOBS_ror_{resource['resource_id']}",
            "provider_id": "PTPRV_ror",
            "endpoint_id": "PTEP_ror_api",
            "source_resource_id": resource["resource_id"],
            "requested_uri": resource.get("url", ""),
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_ror_{resource['resource_id']}",
            "rights_assessment_id": "PTRTS_ror",
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

        if meta.get("name"):
            assertions.append({
                "id": f"PTCAS_ror_{resource_id}_name",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_ror_{resource_id}",
                "predicate": "TITLE", "value": meta["name"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.95,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        entity_candidates.append({
            "id": f"PTCND_ror_{resource_id}",
            "candidate_type": "INSTITUTION",
            "provider_id": "PTPRV_ror",
            "external_resource_id": resource_id,
            "title": meta.get("name", ""),
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        external_ids.append({
            "id": f"PTEXT_ror_{resource_id}",
            "entity_id": f"PTCND_ror_{resource_id}",
            "scheme": "ROR", "value": resource_id,
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


def get_adapter() -> RorAdapter:
    return RorAdapter()
