#!/usr/bin/env python3
"""patala/adapters/crossref/adapter.py — Adapter for Crossref (bibliographic metadata).

Crossref provides DOI metadata including licenses, funding, ORCID/ROR identifiers.
API: https://api.crossref.org/works

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.hashing import uuid7
from patala.adapters.base import SourceAdapter


CROSSREF_API = "https://api.crossref.org/works"


class CrossrefAdapter(SourceAdapter):
    """Adapter for Crossref bibliographic metadata."""

    source_id = "crossref"
    adapter_version = "0.1.0"

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        start = int(cursor) if cursor else 0
        params = {"query": "sanskrit", "rows": str(limit), "offset": str(start)}
        url = f"{CROSSREF_API}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "openpatala/1.0 (mailto:dev@patala.org)"
            })
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            return {"items": [], "next_cursor": None, "source_id": self.source_id, "total": 0, "error": str(e)}

        items = []
        for item in data.get("message", {}).get("items", []):
            authors = [a.get("family", "") + " " + a.get("given", "") for a in item.get("author", [])]
            items.append({
                "resource_id": item.get("DOI", ""),
                "title": (item.get("title", [""])[0] if item.get("title") else ""),
                "authors": authors,
                "publisher": item.get("publisher", ""),
                "type": item.get("type", ""),
                "url": item.get("URL", ""),
            })

        total = data.get("message", {}).get("total-results", 0)
        next_cursor = str(start + limit) if start + limit < total else None
        return {"items": items, "next_cursor": next_cursor, "source_id": self.source_id, "total": total}

    async def fetch_metadata(self, resource: dict) -> dict:
        return {
            "id": f"PTOBS_cr_{resource['resource_id']}",
            "provider_id": "PTPRV_crossref",
            "endpoint_id": "PTEP_crossref_api",
            "source_resource_id": resource["resource_id"],
            "requested_uri": resource.get("url", ""),
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_cr_{resource['resource_id']}",
            "rights_assessment_id": "PTRTS_crossref",
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
                "id": f"PTCAS_cr_{resource_id}_title",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_cr_{resource_id}",
                "predicate": "TITLE", "value": meta["title"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.95,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        for author in meta.get("authors", []):
            if author.strip():
                assertions.append({
                    "id": f"PTCAS_cr_{resource_id}_author_{hash(author) % 10000}",
                    "observation_id": observation.get("id", ""),
                    "subject_candidate_id": f"PTCND_cr_{resource_id}",
                    "predicate": "AUTHOR", "value": author.strip(),
                    "extraction_method": "STRUCTURED_FIELD",
                    "extractor_version": self.adapter_version,
                    "confidence": 0.9,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })

        entity_candidates.append({
            "id": f"PTCND_cr_{resource_id}",
            "candidate_type": "WORK",
            "provider_id": "PTPRV_crossref",
            "external_resource_id": resource_id,
            "title": meta.get("title", ""),
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        if resource_id:
            external_ids.append({
                "id": f"PTEXT_cr_{resource_id}_doi",
                "entity_id": f"PTCND_cr_{resource_id}",
                "scheme": "DOI", "value": resource_id,
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


def get_adapter() -> CrossrefAdapter:
    return CrossrefAdapter()
