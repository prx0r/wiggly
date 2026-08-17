#!/usr/bin/env python3
"""patala/adapters/muktabodha/adapter.py — Adapter for Muktabodha Digital Library.

Muktabodha holds 3,000+ preserved Sanskrit texts (570+ searchable e-texts).
Source: zip archives at /root/patalacheckpoints/source-evidence/repos/project-vyasa__muktabodha.org/data/archives/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.hashing import uuid7
from patala.adapters.base import SourceAdapter


MUKTABODHA_ARCHIVES = Path("/root/patalacheckpoints/source-evidence/repos/project-vyasa__muktabodha.org/data/archives")


class MuktabodhaAdapter(SourceAdapter):
    """Adapter for Muktabodha Digital Library (zip archives)."""

    source_id = "muktabodha"
    adapter_version = "0.1.0"

    def __init__(self):
        self._files = self._list_files()

    def _list_files(self) -> list:
        """List all text files in the IAST zip archive."""
        zip_path = MUKTABODHA_ARCHIVES / "MUKTABODHA-LIBRARY-IAST_2026_02_20.zip"
        if not zip_path.exists():
            return []
        files = []
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.txt') and not name.startswith('__MACOSX'):
                    files.append(name)
        return files

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        items = []
        start = 0
        if cursor:
            for i, f in enumerate(self._files):
                if f == cursor:
                    start = i + 1
                    break

        for fname in self._files[start:start + limit]:
            # Parse filename: AcArasAratantra-M00501-IAST.txt
            parts = fname.replace('-IAST.txt', '').rsplit('-', 1)
            title = parts[0].replace('_', ' ') if len(parts) == 2 else fname
            mukid = parts[1] if len(parts) == 2 else ""

            items.append({
                "resource_id": mukid or fname,
                "title": title,
                "filename": fname,
                "script": "IAST",
                "url": f"muktabodha://{fname}",
            })

        next_cursor = self._files[start + limit] if start + limit < len(self._files) else None
        return {"items": items, "next_cursor": next_cursor, "source_id": self.source_id, "total": len(self._files)}

    async def fetch_metadata(self, resource: dict) -> dict:
        return {
            "id": f"PTOBS_muk_{resource['resource_id']}",
            "provider_id": "PTPRV_muktabodha",
            "endpoint_id": "PTEP_muktabodha_zip",
            "source_resource_id": resource["resource_id"],
            "requested_uri": resource.get("url", ""),
            "resolved_uri": None,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response_metadata_artifact": None,
            "payload_artifact_id": f"PTART_muk_{resource['resource_id']}",
            "rights_assessment_id": "PTRTS_muktabodha",
            "run_id": None,
            "source_state": {},
            "status": "FETCHED",
            "_meta": resource,
        }

    async def fetch_content(self, resource: dict) -> dict | None:
        """Extract text content from zip archive."""
        zip_path = MUKTABODHA_ARCHIVES / "MUKTABODHA-LIBRARY-IAST_2026_02_20.zip"
        filename = resource.get("filename", "")
        if not zip_path.exists() or not filename:
            return None
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                content = zf.read(filename).decode('utf-8', errors='replace')
                return {
                    "id": f"PTART_muk_{resource['resource_id']}_content",
                    "digests": [{"algorithm": "sha256", "value": hashlib.sha256(content.encode()).hexdigest()}],
                    "media_type": "text/plain",
                    "byte_length": len(content.encode()),
                    "storage_uri": f"zip://{zip_path}!{filename}",
                    "availability_state": "PRESENT",
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
        except Exception:
            return None

    async def normalize(self, observation: dict) -> dict:
        meta = observation.get("_meta", {})
        resource_id = observation.get("source_resource_id", "")
        assertions = []
        entity_candidates = []
        external_ids = []

        if meta.get("title"):
            assertions.append({
                "id": f"PTCAS_muk_{resource_id}_title",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_muk_{resource_id}",
                "predicate": "TITLE", "value": meta["title"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.85,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        entity_candidates.append({
            "id": f"PTCND_muk_{resource_id}",
            "candidate_type": "ETEXT",
            "provider_id": "PTPRV_muktabodha",
            "external_resource_id": resource_id,
            "title": meta.get("title", ""),
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        external_ids.append({
            "id": f"PTEXT_muk_{resource_id}",
            "entity_id": f"PTCND_muk_{resource_id}",
            "scheme": "OTHER", "value": resource_id,
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


def get_adapter() -> MuktabodhaAdapter:
    return MuktabodhaAdapter()
