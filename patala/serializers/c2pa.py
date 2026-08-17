#!/usr/bin/env python3
"""patala/serializers/c2pa.py — C2PA media provenance serializer.

Embeds C2PA provenance manifests into Pāṭala-produced media.
Spec: https://c2pa.org/specifications/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import time
from typing import Any


def create_c2pa_manifest(media_type: str, generator: str = "OpenPatala",
                          prompt: str = "", model: str = "",
                          assertion_id: str = "") -> dict:
    """Create a C2PA manifest for a Pāṭala-produced media artifact.

    Per newbuildplayers: "C2PA answers: Where did this media artifact come from?
    Pāṭala answers: Which things depicted in it are actually warranted?"
    """
    manifest = {
        "claim_generator": generator,
        "claim_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "media_type": media_type,
        "assertion_id": assertion_id,
    }

    if model:
        manifest["software_agent"] = {
            "name": model,
            "version": "1.0",
        }

    if prompt:
        manifest["prompt"] = prompt

    # Link to Pāṭala provenance
    manifest["patala_provenance"] = {
        "assertion_id": assertion_id,
        "note": "Which things depicted are actually warranted",
    }

    return manifest


def serialize_manifest_for_media(media_path: str, assertion_id: str = "") -> dict:
    """Create C2PA manifest for a media file."""
    return create_c2pa_manifest(
        media_type="image/png",
        generator="OpenPatala",
        assertion_id=assertion_id,
    )
