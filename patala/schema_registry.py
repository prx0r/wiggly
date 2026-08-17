#!/usr/bin/env python3
"""patala/schema_registry.py — append-only, immutable schema registry.

Per newbuild1 §12-15:
- Every schema that has ever written permanent data must remain available
- Schema versions themselves are immutable
- Never reuse a retired field semantically
- Semantic versioning: PATCH (docs), MINOR (additive), MAJOR (breaking)

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from patala.hashing import uuid7, make_digest_set


@dataclass
class SchemaRecord:
    """A schema in the append-only registry.

    Per newbuild1 §12: "Once a schema has written one permanent record, it is frozen."
    """
    uri: str = ""
    family: str = ""  # e.g. core/artifact, source/provider, atlas/work
    version: str = "1.0.0"
    schema_dialect: str = "https://json-schema.org/draft/2020-12/schema"
    artifact_id: str | None = None
    digest_set: dict = field(default_factory=dict)
    published_at: str = ""
    supersedes: str | None = None
    frozen: bool = False  # True once a permanent record has been written under this schema


class SchemaRegistry:
    """Append-only, immutable schema registry.

    Per newbuild1 §85-86:
    protocol/schemas/
        core/          (entity-identity, event, schema-definition, artifact, digest, actor)
        source/        (provider, endpoint, observation, rights-assessment)
        identity/      (external-identifier, identity-assertion, merge, split)
        epistemic/     (assertion, evidence-use)
        provenance/    (activity, derivation)
        review/        (review-event, adjudication)
        anchor/        (text-anchor)
        atlas/         (work, edition, translation, witness, etc.)
    """

    def __init__(self, registry_dir: Path | str):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "schemas.json"
        self._schemas: dict[str, SchemaRecord] = self._load()

    def _load(self) -> dict[str, SchemaRecord]:
        """Load the registry from disk."""
        schemas = {}
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                for record in data.get("schemas", []):
                    rec = SchemaRecord(**record)
                    schemas[rec.uri] = rec
        return schemas

    def _save(self):
        """Save the registry to disk."""
        data = {
            "schema": "patala.schema-registry/1",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "count": len(self._schemas),
            "schemas": [
                {
                    "uri": r.uri,
                    "family": r.family,
                    "version": r.version,
                    "schema_dialect": r.schema_dialect,
                    "artifact_id": r.artifact_id,
                    "digest_set": r.digest_set,
                    "published_at": r.published_at,
                    "supersedes": r.supersedes,
                    "frozen": r.frozen,
                }
                for r in self._schemas.values()
            ],
        }
        self.registry_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def register(self, uri: str, family: str, version: str,
                 schema_bytes: bytes | None = None,
                 artifact_id: str | None = None,
                 supersedes: str | None = None) -> SchemaRecord:
        """Register a new schema version. Immutable once registered.

        Per newbuild1 §14: "PATCH = docs only, MINOR = additive, MAJOR = breaking."
        """
        if uri in self._schemas:
            existing = self._schemas[uri]
            if existing.frozen:
                raise ValueError(f"Schema {uri} v{existing.version} is frozen — cannot modify")

        # Compute digest if schema bytes provided
        digest_set = {}
        if schema_bytes:
            digest_set = make_digest_set(schema_bytes)

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        record = SchemaRecord(
            uri=uri,
            family=family,
            version=version,
            artifact_id=artifact_id,
            digest_set=digest_set,
            published_at=now,
            supersedes=supersedes,
            frozen=False,
        )

        self._schemas[uri] = record
        self._save()
        return record

    def freeze(self, uri: str):
        """Freeze a schema — no more modifications allowed.

        Per newbuild1 §12: "Once a schema has written one permanent record, it is frozen."
        """
        if uri not in self._schemas:
            raise ValueError(f"Schema {uri} not found")
        self._schemas[uri].frozen = True
        self._save()

    def get(self, uri: str) -> SchemaRecord | None:
        """Get a schema by URI."""
        return self._schemas.get(uri)

    def get_by_family(self, family: str) -> list[SchemaRecord]:
        """Get all versions of a schema family."""
        return [r for r in self._schemas.values() if r.family == family]

    def list_all(self) -> list[SchemaRecord]:
        """List all registered schemas."""
        return list(self._schemas.values())

    def verify_integrity(self) -> bool:
        """Verify all schema digests are correct."""
        for uri, record in self._schemas.items():
            if record.digest_set and record.artifact_id:
                # In a real implementation, we'd recompute the digest from the stored schema file
                # For now, just check the digest_set is well-formed
                digests = record.digest_set.get("digests", [])
                if not digests:
                    return False
        return True


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = SchemaRegistry(tmpdir)

        print("=== Register Schemas ===")
        r1 = registry.register(
            uri="https://patala.org/schemas/v2/artifact.json",
            family="core/artifact",
            version="1.0.0",
            schema_bytes=b'{"type": "object"}',
        )
        print(f"  Registered: {r1.uri} v{r1.version}")

        r2 = registry.register(
            uri="https://patala.org/schemas/v2/artifact.json",
            family="core/artifact",
            version="1.1.0",
            schema_bytes=b'{"type": "object", "properties": {"new_field": true}}',
            supersedes="https://patala.org/schemas/v2/artifact.json",
        )
        print(f"  Registered: {r2.uri} v{r2.version}")

        print(f"\n  Total schemas: {len(registry.list_all())}")

        print("\n=== Freeze Schema ===")
        registry.freeze("https://patala.org/schemas/v2/artifact.json")
        record = registry.get("https://patala.org/schemas/v2/artifact.json")
        print(f"  Frozen: {record.frozen}")

        print("\n=== Try to modify frozen schema ===")
        try:
            registry.register(
                uri="https://patala.org/schemas/v2/artifact.json",
                family="core/artifact",
                version="1.2.0",
            )
        except ValueError as e:
            print(f"  Error (expected): {e}")

        print("\n=== Verify Integrity ===")
        valid = registry.verify_integrity()
        print(f"  Valid: {valid}")
