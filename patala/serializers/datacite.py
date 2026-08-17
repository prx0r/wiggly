#!/usr/bin/env python3
"""patala/serializers/datacite.py — DataCite metadata serializer.

Exports Pāṭala datasets as DataCite-compatible metadata for DOI minting.
Spec: https://datacite-metadata-schema.readthedocs.io/en/4.6/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import time
from typing import Any


def serialize_dataset(dataset_id: str, title: str, creators: list[dict],
                      description: str = "", publication_year: int = None,
                      versions: list[dict] = None) -> dict:
    """Create DataCite metadata for a Pāṭala dataset.

    Per newbuild1 §28: "Snapshots should be citable via DataCite DOIs."
    """
    now = time.strftime("%Y-%m-%d", time.gmtime())
    year = publication_year or int(now[:4])

    metadata = {
        "data": {
            "type": "dois",
            "attributes": {
                "prefix": "10.xxxx/patala",  # placeholder prefix
                "identifiers": [{"identifier": dataset_id, "identifierType": "Handle"}],
                "titles": [{"title": title}],
                "creators": [{"name": c.get("name", ""), "nameType": "Personal"} for c in creators],
                "descriptions": [{"description": description, "descriptionType": "Abstract"}],
                "publisher": "OpenPatala",
                "publicationYear": year,
                "types": {"resourceTypeGeneral": "Dataset", "resourceType": "Scholarly Database"},
                "schemaVersion": "https://datacite.org/schema/schema-4.6.mds",
            },
        }
    }

    if versions:
        metadata["data"]["attributes"]["relatedIdentifiers"] = [
            {"relatedIdentifier": v.get("doi", ""), "relatedIdentifierType": "DOI",
             "relationType": "IsNewVersionOf", "resourceTypeGeneral": "Dataset"}
            for v in versions if v.get("doi")
        ]

    return metadata


def serialize_snapshot_manifest(manifest: dict) -> dict:
    """Create DataCite metadata for a Pāṭala snapshot release."""
    return serialize_dataset(
        dataset_id=manifest.get("snapshot_id", ""),
        title=f"OpenPatala Snapshot {manifest.get('created_at', '')[:10]}",
        creators=[{"name": "OpenPatala Project"}],
        description=f"Scholarly state machine snapshot at event cursor {manifest.get('state_cursor', '')}",
    )
