#!/usr/bin/env python3
"""patala/adapters/orcid/adapter.py — Adapter for ORCID (researcher identity).

ORCID provides persistent researcher identifiers via REST API.
API: https://pub.orcid.org/v3.0/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.hashing import uuid7
from patala.adapters.base import SourceAdapter


ORCID_API = "https://pub.orcid.org/v3.0"


class OrcidAdapter(SourceAdapter):
    """Adapter for ORCID researcher identity."""

    source_id = "orcid"
    adapter_version = "0.1.0"

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        """Search ORCID for researchers working on Sanskrit."""
        search_url = f"{ORCID_API}/search?q=sanskrit&rows={limit}"
        if cursor:
            search_url += f"&start={cursor}"

        try:
            req = urllib.request.Request(search_url, headers={
                "Accept": "application/json",
                "User-Agent": "openpatala/1.0"
            })
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            return {"items": [], "next_cursor": None, "source_id": self.source_id, "total": 0, "error": str(e)}

        items = []
        for result in data.get("result", []):
            person = result.get("orcid-transaction", {}).get("orcid-profile", {}).get("orcid-bio", {})
            name = person.get("personal-details", {}).get("given-names", {}).get("value", "")
            family = person.get("personal-details", {}).get("family-name", {}).get("value", "")
            orcid_id = result.get("orcid-transaction", {}).get("orcid-profile", {}).get("orcid-identifier", {}).get("path", "")

            items.append({
                "resource_id": orcid_id,
                "name": f"{name} {family}".strip(),
                "orcid_id": orcid_id,
            })

        total = data.get("num-found", 0)
        next_cursor = str(len(items)) if len(items) < total else None
        return {"items": items, "next_cursor": next_cursor, "source_id": self.source_id, "total": total}

    async def fetch_metadata(self, resource: dict) -> dict:
        return {
            "id": f"PTOBS_orcid_{resource['resource_id']}",
            "provider_id": "PTPRV_orcid",
            "endpoint_id": "PTEP_orcid_api",
            "source_resource_id": resource["resource_id"],
            "requested_uri": f"https://orcid.org/{resource['resource_id']}",
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_orcid_{resource['resource_id']}",
            "rights_assessment_id": "PTRTS_orcid",
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
                "id": f"PTCAS_orcid_{resource_id}_name",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_orcid_{resource_id}",
                "predicate": "TITLE", "value": meta["name"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.95,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        entity_candidates.append({
            "id": f"PTCND_orcid_{resource_id}",
            "candidate_type": "PERSON",
            "provider_id": "PTPRV_orcid",
            "external_resource_id": resource_id,
            "title": meta.get("name", ""),
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        external_ids.append({
            "id": f"PTEXT_orcid_{resource_id}",
            "entity_id": f"PTCND_orcid_{resource_id}",
            "scheme": "ORCID", "value": resource_id,
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


def get_adapter() -> OrcidAdapter:
    return OrcidAdapter()
