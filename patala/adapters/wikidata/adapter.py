#!/usr/bin/env python3
"""patala/adapters/wikidata/adapter.py — Adapter for WikiData (SPARQL).

WikiData provides structured knowledge about entities via SPARQL endpoint.
Endpoint: https://query.wikidata.org/sparql

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


WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"


class WikiDataAdapter(SourceAdapter):
    """Adapter for WikiData SPARQL endpoint."""

    source_id = "wikidata"
    adapter_version = "0.1.0"

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        """Search WikiData for Sanskrit works via SPARQL."""
        query = """
        SELECT ?item ?itemLabel ?authorLabel WHERE {
          ?item wdt:P31 wd:Q172953 .
          ?item wdt:P136 wd:Q11966 .
          OPTIONAL { ?item wdt:P50 ?author }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en,sa" }
        } LIMIT %d
        """ % limit

        try:
            url = f"{WIKIDATA_SPARQL}?query={urllib.parse.quote(query)}&format=json"
            req = urllib.request.Request(url, headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "openpatala/1.0 (mailto:dev@patala.org)"
            })
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            return {"items": [], "next_cursor": None, "source_id": self.source_id, "total": 0, "error": str(e)}

        items = []
        for binding in data.get("results", {}).get("bindings", []):
            qid = binding.get("item", {}).get("value", "").split("/")[-1]
            items.append({
                "resource_id": qid,
                "title": binding.get("itemLabel", {}).get("value", ""),
                "author": binding.get("authorLabel", {}).get("value", ""),
                "url": f"https://www.wikidata.org/wiki/{qid}",
            })

        return {"items": items, "next_cursor": None, "source_id": self.source_id, "total": len(items)}

    async def fetch_metadata(self, resource: dict) -> dict:
        return {
            "id": f"PTOBS_wd_{resource['resource_id']}",
            "provider_id": "PTPRV_wikidata",
            "endpoint_id": "PTEP_wikidata_sparql",
            "source_resource_id": resource["resource_id"],
            "requested_uri": resource.get("url", ""),
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_wd_{resource['resource_id']}",
            "rights_assessment_id": "PTRTS_wikidata",
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
                "id": f"PTCAS_wd_{resource_id}_title",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_wd_{resource_id}",
                "predicate": "TITLE", "value": meta["title"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.9,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        if meta.get("author"):
            assertions.append({
                "id": f"PTCAS_wd_{resource_id}_author",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_wd_{resource_id}",
                "predicate": "AUTHOR", "value": meta["author"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.85,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        entity_candidates.append({
            "id": f"PTCND_wd_{resource_id}",
            "candidate_type": "WORK",
            "provider_id": "PTPRV_wikidata",
            "external_resource_id": resource_id,
            "title": meta.get("title", ""),
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        external_ids.append({
            "id": f"PTEXT_wd_{resource_id}",
            "entity_id": f"PTCND_wd_{resource_id}",
            "scheme": "WIKIDATA", "value": resource_id,
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


def get_adapter() -> WikiDataAdapter:
    return WikiDataAdapter()
