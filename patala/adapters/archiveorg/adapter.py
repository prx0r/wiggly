#!/usr/bin/env python3
"""patala/adapters/archiveorg/adapter.py — Adapter for Internet Archive.

Archive.org provides free access to millions of digitized texts, manuscripts, and books.
API: https://archive.org/advancedsearch.php

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


ARCHIVE_API = "https://archive.org/advancedsearch.php"


class ArchiveOrgAdapter(SourceAdapter):
    """Adapter for Internet Archive."""

    source_id = "archiveorg"
    adapter_version = "0.1.0"

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        """Search Archive.org for Sanskrit manuscripts."""
        start = int(cursor) if cursor else 0
        params = {
            "q": "sanskrit manuscript",
            "fl[]": "identifier,title,creator,date,subject",
            "rows": str(limit),
            "start": str(start),
            "output": "json",
        }
        url = f"{ARCHIVE_API}?{urllib.parse.urlencode(params, doseq=True)}"

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "openpatala/1.0 (mailto:dev@patala.org)"
            })
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            return {"items": [], "next_cursor": None, "source_id": self.source_id, "total": 0, "error": str(e)}

        docs = data.get("response", {}).get("docs", [])
        total = data.get("response", {}).get("numFound", 0)

        items = []
        for doc in docs:
            items.append({
                "resource_id": doc.get("identifier", ""),
                "title": doc.get("title", ""),
                "creator": doc.get("creator", ""),
                "date": doc.get("date", ""),
                "subject": doc.get("subject", []),
                "url": f"https://archive.org/details/{doc.get('identifier', '')}",
            })

        next_cursor = str(start + limit) if start + limit < total else None
        return {
            "items": items,
            "next_cursor": next_cursor,
            "source_id": self.source_id,
            "total": total,
        }

    async def fetch_metadata(self, resource: dict) -> dict:
        """Fetch metadata for an Archive.org item."""
        return {
            "id": f"PTOBS_ia_{resource['resource_id']}",
            "provider_id": "PTPRV_archiveorg",
            "endpoint_id": "PTEP_archiveorg_api",
            "source_resource_id": resource["resource_id"],
            "requested_uri": resource.get("url", ""),
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_ia_{resource['resource_id']}",
            "rights_assessment_id": "PTRTS_archiveorg",
            "run_id": None,
            "source_state": {},
            "status": "FETCHED",
            "_meta": {
                "title": resource.get("title", ""),
                "creator": resource.get("creator", ""),
                "date": resource.get("date", ""),
                "subject": resource.get("subject", []),
                "identifier": resource["resource_id"],
            },
        }

    async def fetch_content(self, resource: dict) -> dict | None:
        """No content to fetch — metadata only."""
        return None

    async def normalize(self, observation: dict) -> dict:
        """Extract assertions from Archive.org observation."""
        meta = observation.get("_meta", {})
        resource_id = observation.get("source_resource_id", "")
        assertions = []
        entity_candidates = []
        external_ids = []

        # Title assertion
        if meta.get("title"):
            assertions.append({
                "id": f"PTCAS_ia_{resource_id}_title",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_ia_{resource_id}",
                "predicate": "TITLE",
                "value": meta["title"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.9,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Creator assertion
        if meta.get("creator"):
            assertions.append({
                "id": f"PTCAS_ia_{resource_id}_author",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_ia_{resource_id}",
                "predicate": "AUTHOR",
                "value": meta["creator"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.8,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Date assertion
        if meta.get("date"):
            assertions.append({
                "id": f"PTCAS_ia_{resource_id}_date",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_ia_{resource_id}",
                "predicate": "DATE",
                "value": meta["date"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.7,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        # Entity candidate
        entity_candidates.append({
            "id": f"PTCND_ia_{resource_id}",
            "candidate_type": "WORK",
            "provider_id": "PTPRV_archiveorg",
            "external_resource_id": resource_id,
            "title": meta.get("title", ""),
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        # External ID
        external_ids.append({
            "id": f"PTEXT_ia_{resource_id}",
            "entity_id": f"PTCND_ia_{resource_id}",
            "scheme": "ARCHIVE_ORG",
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


def get_adapter() -> ArchiveOrgAdapter:
    return ArchiveOrgAdapter()
