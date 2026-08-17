#!/usr/bin/env python3
"""patala/serializers/ro_crate.py — RO-Crate packaging serializer.

Packages Pāṭala research objects as RO-Crate (JSON-LD + data files).
Spec: https://www.researchobject.org/ro-crate/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def create_ro_crate_metadata(work: dict, files: list[str] = None) -> dict:
    """Create ro-crate-metadata.json for a Pāṭala work.

    Per newbuildplayers: "RO-Crate already exists specifically to package research objects
    with files, identifiers, provenance, people, software, funding and reuse information."
    """
    metadata = {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@type": "Dataset",
                "@id": work.get("id", ""),
                "name": work.get("preferred_title", ""),
                "description": f"Pāṭala scholarly record for {work.get('preferred_title', '')}",
                "license": "https://creativecommons.org/licenses/by-sa/4.0/",
                "creator": {"@type": "Organization", "name": "OpenPatala"},
                "datePublished": time.strftime("%Y-%m-%d", time.gmtime()),
            },
            {
                "@type": "CreativeWork",
                "@id": "ro-crate-metadata.json",
                "conformsTo": "https://w3id.org/ro/crate/1.1",
                "about": {"@id": work.get("id", "")},
            },
        ],
    }

    if files:
        for f in files:
            metadata["@graph"].append({
                "@type": "File",
                "@id": f"file://{f}",
                "name": Path(f).name,
                "about": {"@id": work.get("id", "")},
            })

    return metadata


def package_ro_crate(work: dict, output_dir: str) -> str:
    """Create RO-Crate directory structure."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    metadata = create_ro_crate_metadata(work)
    (out / "ro-crate-metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return str(out)
