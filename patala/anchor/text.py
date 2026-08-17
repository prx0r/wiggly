#!/usr/bin/env python3
"""patala/anchor/text.py — TextAnchor with multiple selectors.

Per newbuild1 §43: "Passages need stronger anchors than offsets.
Use multiple selectors: TextPositionSelector, TextQuoteSelector,
XPathSelector, XmlIdSelector, IIIFSelector."

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patala.hashing import uuid7, make_digest


def create_text_anchor(source_artifact_id: str, text: str,
                       start: int = None, end: int = None,
                       xpath: str = None, xml_id: str = None) -> dict:
    """Create a TextAnchor with multiple selectors.

    Per newbuild1 §43: "Use multiple selectors.
    TextAnchor { source_artifact_id, selectors: [TextPositionSelector,
    TextQuoteSelector, XPathSelector?, XmlIdSelector?, IIIFSelector?] }"
    """
    selectors = []

    # TextPosition selector
    if start is not None and end is not None:
        selectors.append({
            "type": "TextPosition",
            "start": start,
            "end": end,
        })

    # TextQuote selector (exact text + context)
    if text:
        selectors.append({
            "type": "TextQuote",
            "exact": text[:100],
            "prefix": text[:20] if len(text) > 20 else "",
            "suffix": text[-20:] if len(text) > 20 else "",
        })

    # XPath selector
    if xpath:
        selectors.append({
            "type": "XPath",
            "xpath": xpath,
        })

    # XmlId selector
    if xml_id:
        selectors.append({
            "type": "XmlId",
            "xml_id": xml_id,
        })

    # Compute source digest
    source_digest = make_digest(text.encode(), "sha256")

    return {
        "id": f"PTANC_{uuid7().replace(chr(45), '')[:16]}",
        "source_artifact_id": source_artifact_id,
        "selectors": selectors,
        "source_digest": source_digest,
        "normalization_profile": None,
    }


def anchor_to_web_annotation(anchor: dict, body_text: str = "") -> dict:
    """Convert TextAnchor to W3C Web Annotation JSON-LD."""
    selectors = anchor.get("selectors", [])
    target = selectors[0] if selectors else {"type": "TextPositionSelector"}

    return {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "type": "Annotation",
        "body": {"type": "TextualBody", "value": body_text},
        "target": target,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generator": "OpenPatala",
    }
