#!/usr/bin/env python3
"""patala/adapters/openalex/adapter.py — Adapter for OpenAlex scholarly database.

OpenAlex provides free API access to scholarly works, authors, institutions.
No API key required for basic queries.

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


OPENALEX_API = "https://api.openalex.org"


class OpenAlexAdapter(SourceAdapter):
    """Adapter for OpenAlex scholarly database."""

    source_id = "openalex"
    adapter_version = "0.1.0"

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        """Search for scholarly works related to Sanskrit."""
        # Search for works mentioning Sanskrit in title or abstract
        search_url = f"{OPENALEX_API}/works?search=sanskrit&per_page={limit}"
        if cursor:
            search_url += f"&cursor={cursor}"

        try:
            req = urllib.request.Request(search_url, headers={
                "User-Agent": "openpatala/1.0 (mailto:dev@patala.org)"
            })
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            return {"items": [], "next_cursor": None, "source_id": self.source_id, "total": 0, "error": str(e)}

        items = []
        for work in data.get("results", []):
            items.append({
                "resource_id": work.get("id", "").split("/")[-1],
                "title": work.get("title", ""),
                "authorships": [
                    {"author": a.get("author", {}).get("display_name", ""),
                     "institution": a.get("institutions", [{}])[0].get("display_name", "") if a.get("institutions") else ""}
                    for a in work.get("authorships", [])
                ],
                "publication_year": work.get("publication_year"),
                "doi": work.get("doi"),
                "cited_by_count": work.get("cited_by_count", 0),
                "openalex_id": work.get("id", ""),
                "type": work.get("type", ""),
            })

        next_cursor = data.get("meta", {}).get("next_cursor")
        return {
            "items": items,
            "next_cursor": next_cursor,
            "source_id": self.source_id,
            "total": data.get("meta", {}).get("count", 0),
        }

    async def fetch_metadata(self, resource: dict) -> dict:
        """Fetch metadata for a scholarly work."""
        return {
            "id": f"PTOBS_oa_{resource.get('resource_id', '')}",
            "provider_id": "PTPRV_openalex",
            "endpoint_id": "PTEP_openalex_api",
            "source_resource_id": resource.get("resource_id", ""),
            "requested_uri": resource.get("openalex_id", ""),
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_oa_{resource.get('resource_id', '')}",
            "rights_assessment_id": "PTRTS_openalex",
            "run_id": None,
            "source_state": {},
            "status": "FETCHED",
            "_meta": {
                "title": resource.get("title", ""),
                "authorships": resource.get("authorships", []),
                "publication_year": resource.get("publication_year"),
                "doi": resource.get("doi"),
                "cited_by_count": resource.get("cited_by_count", 0),
                "openalex_id": resource.get("openalex_id", ""),
                "type": resource.get("type", ""),
            },
        }

    async def fetch_content(self, resource: dict) -> dict | None:
        """No content to fetch — OpenAlex is metadata-only."""
        return None

    async def normalize(self, observation: dict) -> dict:
        """Extract assertions from OpenAlex observation."""
        meta = observation.get("_meta", {})
        resource_id = observation.get("source_resource_id", "")
        assertions = []
        entity_candidates = []
        external_ids = []

        # Title assertion
        if meta.get("title"):
            assertions.append({
                "id": f"PTCAS_oa_{resource_id}_title",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_oa_{resource_id}",
                "predicate": "TITLE",
                "value": meta["title"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.95,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Author assertions
        for authorship in meta.get("authorships", []):
            author_name = authorship.get("author", "")
            if author_name:
                assertions.append({
                    "id": f"PTCAS_oa_{resource_id}_author_{hash(author_name) % 10000}",
                    "observation_id": observation.get("id", ""),
                    "subject_candidate_id": f"PTCND_oa_{resource_id}",
                    "predicate": "AUTHOR",
                    "value": author_name,
                    "extraction_method": "STRUCTURED_FIELD",
                    "extractor_version": self.adapter_version,
                    "confidence": 0.9,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })

        # Publication year assertion
        if meta.get("publication_year"):
            assertions.append({
                "id": f"PTCAS_oa_{resource_id}_year",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_oa_{resource_id}",
                "predicate": "DATE",
                "value": str(meta["publication_year"]),
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.95,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Entity candidate
        entity_candidates.append({
            "id": f"PTCND_oa_{resource_id}",
            "candidate_type": "WORK",
            "provider_id": "PTPRV_openalex",
            "external_resource_id": resource_id,
            "title": meta.get("title", ""),
            "author": meta.get("authorships", [{}])[0].get("author", "") if meta.get("authorships") else "",
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        # External IDs
        if meta.get("openalex_id"):
            external_ids.append({
                "id": f"PTEXT_oa_{resource_id}_openalex",
                "entity_id": f"PTCND_oa_{resource_id}",
                "scheme": "OTHER",
                "value": meta["openalex_id"],
                "source_observation_id": observation.get("id", ""),
                "relation_confidence": 1.0,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
        if meta.get("doi"):
            external_ids.append({
                "id": f"PTEXT_oa_{resource_id}_doi",
                "entity_id": f"PTCND_oa_{resource_id}",
                "scheme": "DOI",
                "value": meta["doi"],
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


def get_adapter() -> OpenAlexAdapter:
    return OpenAlexAdapter()
