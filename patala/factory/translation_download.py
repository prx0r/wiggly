#!/usr/bin/env python3
"""pipeline/translation_download.py — F1+F2+F3+F5+F6: enrich translation editions with download-proof,
tier/quality, coverage, and the evidence ladder. (SPEC-TRANSLATION-DOWNLOAD-LAYER.md)

The deepfinder finds WHERE a translation is. This kernel proves whether it's actually DOWNLOADABLE
(and how), what quality it is (tier A/B/C), what it covers, and where it sits on the evidence ladder.

Per edition, based on `source`:
  archive.org  → /metadata/{identifier} → files[] probe: _djvu.txt (OCR text), _text.pdf, .pdf, _abbyy
                  → downloadable, formats[], bytes, live_confirmed, tier (B if only OCR)
  openlibrary  → ebook_access (public|borrowable|printdisabled|no_ebook) → downloadable + access
                  → tier by author/title heuristics (A for scholarly, B for scans)

Deterministic, polite (UA+mailto, sleep, fail-closed), CPU-only. Reused by the availability compile step.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

USER_AGENT = "patala-translation-download/0.1 (mailto:dev@patala.local)"

# deterministic tier rules (see spec F2)
SCHOLARLY_AUTHORS = ("lakshmanjoo", "jaideva", "dyczkowski", "hughes", "sands", "silburn",
                     "singh", "muktananda", "dyczkowski", "pradipaka", "vasugupta")
UNVERIFIED_TITLE = re.compile(r"\b(ai|hypertuned|auto)\b", re.I)

# the evidence ladder (spec F6)
LADDER = ("DISCOVERED", "CATALOG_MATCHED", "DOWNLOAD_CONFIRMED", "TEXT_EXTRACTED", "SCHOLAR_CONFIRMED")


def _get_json(url: str, timeout: int = 25) -> dict:
    try:
        r = subprocess.run(["curl", "-s", "-m", str(timeout), "-A", USER_AGENT, url],
                           capture_output=True, text=True)
        return json.loads(r.stdout or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _head_ok(url: str, timeout: int = 20) -> bool:
    """Live HEAD: does the download URL actually respond 200? Follows redirects (archive.org file
    servers 302 → the actual file host)."""
    r = subprocess.run(["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{http_code}",
                        "-I", "-m", str(timeout), "-A", USER_AGENT, url],
                       capture_output=True, text=True)
    return r.stdout.strip() == "200"


def confirm_archive(identifier: str, live: bool = True) -> dict:
    """Probe an archive.org item → downloadable formats + bytes + tier + live confirmation.

    Records the ACTUAL file path for each format (archive.org identifiers can be camelCase/hyphenated;
    the download URL uses the exact file name, NOT a reconstructed '{id}_djvu.txt')."""
    m = _get_json(f"https://archive.org/metadata/{identifier}")
    files = m.get("files", [])
    formats = []
    total = 0
    for f in files:
        n = f.get("name", "")
        size = f.get("size", 0)
        try:
            size = int(size)
        except (TypeError, ValueError):
            size = 0
        if "_djvu.txt" in n:
            formats.append({"name": n, "kind": "ocr_text", "bytes": size})
            total += size
        elif "_text.pdf" in n or n.endswith(".pdf"):
            formats.append({"name": n, "kind": "pdf", "bytes": size})
            total += size
        elif "_abbyy.gz" in n:
            formats.append({"name": n, "kind": "ocr_xml", "bytes": size})
            total += size
    downloadable = bool(formats)
    # tier: archive items are scans → OCR-derived unless proven otherwise; AI/Hypertuned → unverified C
    title = m.get("metadata", {}).get("title", "")
    tier = "C" if UNVERIFIED_TITLE.search(str(title)) else "B"
    # live confirmation: the actual download URL responds 200 (use the real file name, URL-encoded)
    live_confirmed = False
    if downloadable and live:
        # prefer a plain-text OCR file, else the first PDF
        pick = next((f for f in formats if f["kind"] == "ocr_text"), formats[0])
        url = f"https://archive.org/download/{identifier}/{urllib.parse.quote(pick['name'])}"
        live_confirmed = _head_ok(url)
        time.sleep(0.3)
    return {
        "source": "archive.org", "identifier": identifier,
        "downloadable": downloadable, "formats": formats, "bytes": total,
        "download_path": (f"https://archive.org/download/{identifier}/"
                          f"{urllib.parse.quote(formats[0]['name'])}") if formats else None,
        "live_confirmed": live_confirmed, "tier": tier,
        "authority": "DOWNLOAD_CONFIRMED" if (downloadable and live_confirmed) else
                    ("CATALOG_MATCHED" if downloadable else "DISCOVERED"),
    }


def confirm_openlibrary(edition_key: str, ebook_access: str, title: str, author: str, live: bool = True) -> dict:
    """Enrich an OpenLibrary edition → download access + tier + coverage."""
    downloadable = ebook_access in ("public", "borrowable")
    # tier: scholarly published translations (named translators) → A; otherwise B
    t = f"{author} {title}".lower()
    tier = "A" if any(a in t for a in SCHOLARLY_AUTHORS) else (
        "C" if UNVERIFIED_TITLE.search(title) else "B")
    live_confirmed = False
    url = f"https://openlibrary.org/books/{edition_key}.json"
    if downloadable and live and ebook_access == "public":
        live_confirmed = _head_ok(f"https://openlibrary.org/books/{edition_key}")
        time.sleep(0.3)
    return {
        "source": "openlibrary", "edition_key": edition_key,
        "downloadable": downloadable, "access": ebook_access,
        "live_confirmed": live_confirmed, "tier": tier,
        "authority": "DOWNLOAD_CONFIRMED" if (ebook_access == "public" and live_confirmed) else
                    ("CATALOG_MATCHED" if downloadable else "DISCOVERED"),
    }


def evidence_ladder(authority: str) -> dict:
    """Normalize an authority string to the fixed ladder + return its rank (spec F6)."""
    a = authority.upper() if authority in LADDER else "DISCOVERED"
    return {"authority": a, "rank": LADDER.index(a), "ladder": list(LADDER)}


def enrich_translation(t: dict, live: bool = True) -> dict:
    """Enrich ONE deepfinder translation edition with download-proof + tier + coverage + authority."""
    e = dict(t)
    source = e.get("source", "")
    identifier = e.get("identifier")
    edition_key = e.get("edition_key")
    ebook_access = e.get("ebook_access")

    if source == "archive.org" and identifier:
        c = confirm_archive(identifier, live=live)
        e.update({k: c[k] for k in ("downloadable", "formats", "bytes", "download_path", "live_confirmed", "tier", "authority")})
        e["access"] = "public" if c["downloadable"] else "no_ebook"
        e["quality"] = "ocr" if c["tier"] == "B" else "scholarly"
        e["coverage"] = _coverage_from_title(e.get("title", ""))
    elif source == "openlibrary" and edition_key:
        c = confirm_openlibrary(edition_key, e.get("ebook_access", "no_ebook"),
                                e.get("title", ""), e.get("author", ""), live=live)
        e.update({k: c[k] for k in ("downloadable", "access", "live_confirmed", "tier", "authority")})
        e["formats"] = [{"name": "openlibrary_book", "kind": "ebook"}]
        e["quality"] = "scholarly" if c["tier"] == "A" else ("unverified" if c["tier"] == "C" else "ocr")
        e["coverage"] = _coverage_from_title(e.get("title", ""))
    else:
        e.setdefault("downloadable", False)
        e.setdefault("access", "unknown")
        e.setdefault("live_confirmed", False)
        e.setdefault("tier", "B")
        e.setdefault("formats", [])
        e.setdefault("quality", "unknown")
        e.setdefault("coverage", "unknown")
        e["authority"] = "DISCOVERED"

    e["evidence"] = evidence_ladder(e.get("authority", "DISCOVERED"))
    return e


def _coverage_from_title(title: str) -> str:
    """full/partial/excerpts from the edition title (deterministic heuristic)."""
    t = title.lower()
    if any(x in t for x in ("excerpt", "selection", "extract", "chapters 1 thru 14", "volume 1", "part 1",
                            "vidyā", "early chapters")):
        return "partial"
    if any(x in t for x in ("commentary", "translation by", "full")):
        return "full"
    return "full"


def language_matrix(translations: list[dict]) -> dict:
    """F5: per-language navigable matrix from a flat list of enriched translations."""
    m = {}
    for t in translations:
        lang = t.get("language", "unknown")
        d = m.setdefault(lang, {"count": 0, "downloadable": 0, "editions": []})
        d["count"] += 1
        if t.get("downloadable"):
            d["downloadable"] += 1
        d["editions"].append({"title": t.get("title", ""), "year": t.get("year"),
                              "downloadable": t.get("downloadable", False),
                              "tier": t.get("tier", "B"), "authority": t.get("authority", "DISCOVERED"),
                              "url": t.get("url")})
    return m


if __name__ == "__main__":
    # smoke test on a known item
    print(json.dumps(enrich_translation(
        {"source": "openlibrary", "edition_key": "OL3332430M", "ebook_access": "borrowable",
         "title": "Sri Vijnana Bhairava Tantra", "author": "Satyasangananda", "language": "eng",
         "year": 2003, "url": "https://openlibrary.org/books/OL3332430M"},
        live=False), indent=2, ensure_ascii=False))