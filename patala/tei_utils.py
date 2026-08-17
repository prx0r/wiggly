#!/usr/bin/env python3
"""patala/tei_utils.py — Shared TEI XML parsing utilities.

Used by GRETIL, SARIT, and other TEI-based adapters.
Parses critical apparatus, variant readings, and witness lists.

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

# TEI namespace
TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


def parse_tei_header(file_path: str | Path) -> dict:
    """Parse TEI header metadata from a file.

    Returns dict with title, author, language, licence, etc.
    """
    from pathlib import Path
    tree = ET.parse(str(file_path))
    root = tree.getroot()

    header = root.find(f".//{{{TEI_NS}}}teiHeader")
    if header is None:
        return {}

    result = {}

    # Title
    title_el = header.find(f".//{{{TEI_NS}}}titleStmt/{{{TEI_NS}}}title", NS)
    if title_el is not None and title_el.text:
        result["title"] = title_el.text.strip()

    # Author
    author_el = header.find(f".//{{{TEI_NS}}}titleStmt/{{{TEI_NS}}}author", NS)
    if author_el is not None and author_el.text:
        result["author"] = author_el.text.strip()

    # Language
    lang_el = header.find(f".//{{{TEI_NS}}}langUsage/{{{TEI_NS}}}language", NS)
    if lang_el is not None:
        result["language"] = lang_el.get("ident", "unknown")

    # Licence
    licence_el = header.find(f".//{{{TEI_NS}}}publicationStmt/{{{TEI_NS}}}availability/{{{TEI_NS}}}licence", NS)
    if licence_el is not None:
        result["licence"] = licence_el.get("target", "unknown")

    # Publisher
    pub_el = header.find(f".//{{{TEI_NS}}}publicationStmt/{{{TEI_NS}}}publisher", NS)
    if pub_el is not None and pub_el.text:
        result["publisher"] = pub_el.text.strip()

    # Date
    date_el = header.find(f".//{{{TEI_NS}}}publicationStmt/{{{TEI_NS}}}date", NS)
    if date_el is not None:
        result["date"] = date_el.get("when-iso", date_el.text or "")

    return result


def parse_tei_body(file_path: str | Path) -> list[dict]:
    """Parse TEI body content into segments.

    Returns list of dicts with type, text, locator info.
    """
    from pathlib import Path
    tree = ET.parse(str(file_path))
    root = tree.getroot()

    body = root.find(f".//{{{TEI_NS}}}body", NS)
    if body is None:
        return []

    segments = []
    for div in body.iter(f"{{{TEI_NS}}}div"):
        seg_type = div.get("type", "section")
        text = _extract_text(div)
        if text.strip():
            segments.append({
                "type": seg_type,
                "text": text.strip(),
                "xml_id": div.get(f"{{{TEI_NS}}}id", div.get("id", "")),
            })

    return segments


def parse_apparatus(file_path: str | Path) -> list[dict]:
    """Parse critical apparatus (<app>, <rdg>, <wit> elements).

    Returns list of variant readings with witness references.
    """
    from pathlib import Path
    tree = ET.parse(str(file_path))
    root = tree.getroot()

    variants = []
    for app in root.iter(f"{{{TEI_NS}}}app"):
        lemma = ""
        readings = []

        for child in app:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "lem":
                lemma = _extract_text(child)
            elif tag == "rdg":
                wit = child.get("wit", "")
                text = _extract_text(child)
                readings.append({"wit": wit, "text": text})

        if lemma or readings:
            variants.append({
                "lemma": lemma,
                "readings": readings,
                "xml_id": app.get(f"{{{TEI_NS}}}id", app.get("id", "")),
            })

    return variants


def parse_witnesses(file_path: str | Path) -> list[dict]:
    """Parse witness list (<witness> elements).

    Returns list of witness descriptions.
    """
    from pathlib import Path
    tree = ET.parse(str(file_path))
    root = tree.getroot()

    witnesses = []
    for wit in root.iter(f"{{{TEI_NS}}}witness"):
        siglum = wit.get("siglum", wit.get("xml:id", ""))
        text = _extract_text(wit)
        witnesses.append({
            "siglum": siglum,
            "description": text.strip(),
        })

    return witnesses


def _extract_text(element) -> str:
    """Recursively extract all text content from an XML element."""
    parts = []
    if element.text:
        parts.append(element.text)
    for child in element:
        parts.append(_extract_text(child))
        if child.tail:
            parts.append(child.tail)
    return " ".join(parts)
