#!/usr/bin/env python3
"""patala/adapters/stam/adapter.py — STAM annotation adapter.

Integrates Pāṭala TextAnchor with STAM (Stand-off Text Annotation Model).

Per pathway §3: "STAM may be one of the biggest finds."
Per pathway §3: "I would seriously investigate Pāṭala TextAnchor / Annotation ↔ STAM"

STAM assumes: "information about a text is an annotation."
Annotations can target text spans OR other annotations.

Integration:
  Pāṭala TextAnchor → STAM annotation → STAM store
  STAM annotation → Pāṭala EvidenceUse

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.hashing import uuid7


class STAMAdapter:
    """Adapter for STAM annotation model.

    Converts between Pāṭala TextAnchor and STAM annotations.
    STAM is the annotation substrate for Pāṭala passages.
    """

    source_id = "stam"
    adapter_version = "0.1.0"

    def text_anchor_to_stam(self, anchor: dict) -> dict:
        """Convert Pāṭala TextAnchor to STAM annotation format.

        Per pathway §3: "Pāṭala TextAnchor / Annotation ↔ STAM"
        """
        selectors = anchor.get("selectors", [])
        target = {}
        for sel in selectors:
            sel_type = sel.get("type", "")
            if sel_type == "TextPosition":
                target = {
                    "type": "TextSelector",
                    "text": {"set": anchor.get("source_artifact_id", "")},
                    "begin": sel.get("start", 0),
                    "end": sel.get("end", 0),
                }
            elif sel_type == "TextQuote":
                target = {
                    "type": "TextSelector",
                    "text": {"set": anchor.get("source_artifact_id", "")},
                    "quote": sel.get("exact", ""),
                }

        annotation = {
            "type": "Annotation",
            "id": anchor.get("id", f"STAM_{uuid7().replace('-', '')[:16]}"),
            "target": target,
            "body": {
                "type": "TextualBody",
                "value": "",
            },
            "motivation": "linking",
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        return annotation

    def stam_to_text_anchor(self, annotation: dict) -> dict:
        """Convert STAM annotation to Pāṭala TextAnchor."""
        target = annotation.get("target", {})
        selectors = []

        if target.get("type") == "TextSelector":
            if "begin" in target and "end" in target:
                selectors.append({
                    "type": "TextPosition",
                    "start": target["begin"],
                    "end": target["end"],
                })
            if "quote" in target:
                selectors.append({
                    "type": "TextQuote",
                    "exact": target["quote"],
                })

        return {
            "id": annotation.get("id", f"PTANC_{uuid7().replace('-', '')[:16]}"),
            "source_artifact_id": target.get("text", {}).get("set", ""),
            "selectors": selectors,
            "source_digest": {"algorithm": "sha256", "value": ""},
            "normalization_profile": None,
        }

    def create_annotation_set(self, name: str, annotations: list[dict]) -> dict:
        """Create a STAM annotation set from a list of annotations."""
        return {
            "type": "AnnotationSet",
            "id": f"STAMSET_{uuid7().replace('-', '')[:16]}",
            "name": name,
            "annotations": annotations,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


def get_adapter() -> STAMAdapter:
    return STAMAdapter()
