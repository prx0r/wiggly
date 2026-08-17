#!/usr/bin/env python3
"""patala/serializers/web_annotation.py — W3C Web Annotation serializer.

Exports Pāṭala TextAnchor/TextSpan as W3C Web Annotation JSON-LD.
Spec: https://www.w3.org/TR/annotation-model/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import time
from typing import Any


def serialize_annotation(text_anchor: dict, body_text: str = "") -> dict:
    """Convert a Pāṭala TextAnchor to W3C Web Annotation JSON-LD."""
    selectors = []
    for sel in text_anchor.get("selectors", []):
        selector = {"type": sel.get("type", "TextPositionSelector")}
        if sel.get("start") is not None:
            selector["start"] = sel["start"]
        if sel.get("end") is not None:
            selector["end"] = sel["end"]
        if sel.get("exact"):
            selector["exact"] = sel["exact"]
        if sel.get("prefix"):
            selector["prefix"] = sel["prefix"]
        if sel.get("suffix"):
            selector["suffix"] = sel["suffix"]
        selectors.append(selector)

    target = {
        "type": "TextPositionSelector",
        "source": text_anchor.get("source_artifact_id", ""),
    }
    if selectors:
        target = selectors[0]

    annotation = {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "type": "Annotation",
        "body": {
            "type": "TextualBody",
            "value": body_text,
        },
        "target": target,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generator": "OpenPatala",
    }

    return annotation


def serialize_annotations(anchors: list[dict]) -> dict:
    """Create a W3C Web Annotation Collection from multiple anchors."""
    return {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "type": "AnnotationCollection",
        "items": [serialize_annotation(a) for a in anchors],
    }
