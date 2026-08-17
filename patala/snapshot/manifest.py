#!/usr/bin/env python3
"""patala/snapshot/manifest.py — Snapshot manifest with signatures.

Per newbuild1 §27-28: "Every snapshot gets: SnapshotManifest { snapshot_id,
state_cursor, created_at, protocol_version, schemas[], files[], root_digest, signatures }.
Snapshots should be citable via DataCite DOIs."

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patala.hashing import uuid7, make_digest_set, make_digest
from patala.signing.checkpoint import sign_checkpoint
from patala.db import store


def create_snapshot_manifest(state_cursor: int, files: list[dict],
                             schema_versions: list[str] = None) -> dict:
    """Create a SnapshotManifest.

    Per newbuild1 §27: "Every snapshot gets: SnapshotManifest { snapshot_id,
    state_cursor, created_at, protocol_version, schemas[], files[], root_digest, signatures }."
    """
    manifest = {
        "snapshot_id": f"PTSNAP_{uuid7().replace(chr(45), '')[:16]}",
        "state_cursor": state_cursor,
        "previous_snapshot": None,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol_version": "1.0.0",
        "schema_registry_digest": None,
        "ledger_checkpoint": None,
        "schemas": schema_versions or [],
        "files": files,
        "root_digest": {},
        "signatures": [],
    }

    # Compute root digest of the manifest
    manifest_bytes = json.dumps(manifest, sort_keys=True, default=str).encode()
    manifest["root_digest"] = make_digest_set(manifest_bytes)

    return manifest


def sign_snapshot(manifest: dict, algorithm: str = "sha256") -> dict:
    """Sign a snapshot manifest.

    Per newbuild1 §36: "Algorithm-tagged signatures."
    """
    from patala.signing.checkpoint import sign_checkpoint
    signature = sign_checkpoint(manifest, algorithm=algorithm)
    manifest["signatures"].append(signature)
    return manifest


def save_snapshot(manifest: dict, output_dir: str) -> str:
    """Save snapshot manifest to disk."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    manifest_file = output / f"manifest-{manifest['snapshot_id']}.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    return str(manifest_file)
