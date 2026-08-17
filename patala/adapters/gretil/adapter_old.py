#!/usr/bin/env python3
"""GRETIL adapter — discovers and ingests Sanskrit e-texts from the GRETIL corpus.

GRETIL provides TEI XML files with:
- titleStmt (title, author)
- publicationStmt (publisher, availability, licence)
- notesStmt (notes about the text)
- The actual text content (verse/prose)

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# GRETIL repo path
GRETIL_REPO = Path("/root/patalacheckpoints/source-evidence/repos/INDOLOGY__GRETIL-mirror")
GRETIL_TEI = GRETIL_REPO / "gretil.sub.uni-goettingen.de" / "gretil" / "corpustei"

# TEI namespace
NS = {"tei": "http://www.tei-c.org/ns/1.0"}


class GretilAdapter:
    """Adapter for the GRETIL corpus of Sanskrit e-texts."""

    source_id = "gretil"
    adapter_version = "0.1.0"

    def __init__(self):
        self.tei_dir = GRETIL_TEI

    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        """Discover all TEI XML files in the GRETIL corpus."""
        items = []
        xml_files = sorted(self.tei_dir.glob("*.xml"))

        # Apply cursor pagination
        start_idx = 0
        if cursor:
            for i, f in enumerate(xml_files):
                if f.name == cursor:
                    start_idx = i + 1
                    break

        for f in xml_files[start_idx:start_idx + limit]:
            try:
                meta = self._parse_tei_header(f)
                items.append({
                    "resource_id": f.stem,
                    "title": meta.get("title", f.stem),
                    "author": meta.get("author", "unknown"),
                    "url": f"file://{f}",
                    "filename": f.name,
                    "language": meta.get("language", "san"),
                    "licence": meta.get("licence", "unknown"),
                })
            except Exception as e:
                items.append({
                    "resource_id": f.stem,
                    "title": f.stem,
                    "url": f"file://{f}",
                    "error": str(e),
                })

        next_cursor = xml_files[start_idx + limit].name if start_idx + limit < len(xml_files) else None
        return {
            "items": items,
            "next_cursor": next_cursor,
            "source_id": self.source_id,
            "total": len(xml_files),
        }

    async def fetch_metadata(self, resource: dict) -> dict:
        """Fetch metadata from a TEI XML file."""
        resource_id = resource.get("resource_id", "")
        f = self.tei_dir / f"{resource_id}.xml"
        if not f.exists():
            return {"error": f"File not found: {f}"}

        meta = self._parse_tei_header(f)
        content = f.read_bytes()
        content_hash = hashlib.sha256(content).hexdigest()

        return {
            "id": f"PTOBS_{resource_id}",
            "provider_id": "PTPRV_gretil",
            "endpoint_id": "PTEP_gretil_tei",
            "external_resource_id": resource_id,
            "source_url": f"file://{f}",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "http_status": 200,
            "mime_type": "application/xml",
            "artifact_id": None,  # will be set after artifact creation
            "payload_hash": f"sha256:{content_hash}",
            "acquisition_method": "IMPORT",
            "rights_policy_id": "PTRTS_gretil",
            "crawl_run_id": None,
            "headers_subset": {},
            "status": "FETCHED",
            # Extra metadata for normalization
            "_meta": meta,
            "_file_path": str(f),
        }

    async def fetch_content(self, resource: dict) -> dict | None:
        """Fetch the TEI XML content."""
        resource_id = resource.get("resource_id", "")
        f = self.tei_dir / f"{resource_id}.xml"
        if not f.exists():
            return None

        content = f.read_bytes()
        content_hash = hashlib.sha256(content).hexdigest()

        return {
            "id": f"PTART_{resource_id}_tei",
            "digests": [{"algorithm": "sha256", "value": content_hash}],
            "media_type": "application/xml",
            "byte_length": len(content),
            "storage_uri": f"file://{f}",
            "compression": None,
            "encoding": "utf-8",
            "rights_assessment_ids": ["PTRTS_gretil"],
            "availability_state": "PRESENT",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def normalize(self, observation: dict) -> dict:
        """Extract CandidateAssertions from a GRETIL observation."""
        meta = observation.get("_meta", {})
        resource_id = observation.get("external_resource_id", "")
        assertions = []
        entity_candidates = []
        external_ids = []

        # Extract title assertion
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
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        # Extract author assertion
        if meta.get("author") and meta["author"] != "unknown":
            assertions.append({
                "id": f"PTCAS_{resource_id}_author",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_{resource_id}",
                "predicate": "AUTHOR",
                "value": meta["author"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.9,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        # Extract language assertion
        if meta.get("language"):
            assertions.append({
                "id": f"PTCAS_{resource_id}_lang",
                "observation_id": observation.get("id", ""),
                "subject_candidate_id": f"PTCND_{resource_id}",
                "predicate": "LANGUAGE",
                "value": meta["language"],
                "extraction_method": "STRUCTURED_FIELD",
                "extractor_version": self.adapter_version,
                "confidence": 0.99,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        # Create entity candidate
        entity_candidates.append({
            "id": f"PTCND_{resource_id}",
            "candidate_type": "ETEXT",
            "provider_id": "PTPRV_gretil",
            "external_resource_id": resource_id,
            "assertion_ids": [a["id"] for a in assertions],
            "normalized_fingerprint": self._fingerprint(meta),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        # External ID
        external_ids.append({
            "id": f"PTEXT_{resource_id}_gretil",
            "entity_id": f"PTCND_{resource_id}",
            "scheme": "GRETIL",
            "value": resource_id,
            "source_observation_id": observation.get("id", ""),
            "relation_confidence": 1.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
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

    async def changes_since(self, cursor: str | None = None) -> dict:
        """GRETIL is a static corpus — no incremental changes."""
        return await self.discover(cursor=cursor)

    def _parse_tei_header(self, f: Path) -> dict:
        """Parse the TEI header to extract metadata."""
        try:
            tree = ET.parse(f)
            root = tree.getroot()

            title_el = root.find(".//tei:titleStmt/tei:title", NS)
            author_el = root.find(".//tei:titleStmt/tei:author", NS)
            licence_el = root.find(".//tei:publicationStmt/tei:availability/tei:licence", NS)
            language_el = root.find(".//tei:langUsage/tei:language", NS)

            return {
                "title": title_el.text.strip() if title_el is not None and title_el.text else None,
                "author": author_el.text.strip() if author_el is not None and author_el.text else "unknown",
                "licence": licence_el.get("target", "unknown") if licence_el is not None else "unknown",
                "language": language_el.get("ident", "san") if language_el is not None else "san",
            }
        except Exception:
            return {"title": f.stem, "author": "unknown", "language": "san"}

    def _fingerprint(self, meta: dict) -> str:
        """Create a normalized fingerprint for deduplication."""
        title = (meta.get("title") or "").lower().strip()
        author = (meta.get("author") or "").lower().strip()
        # Simple fingerprint: title + author hash
        raw = f"{title}|{author}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_adapter() -> GretilAdapter:
    return GretilAdapter()
