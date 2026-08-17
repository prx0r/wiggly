#!/usr/bin/env python3
"""patala/factory/download.py — Translation download verification (Postgres-backed).

Proves whether translations are actually DOWNLOADABLE, what quality (tier A/B/C),
what coverage, and where they sit on the evidence ladder.

Per newbuildmainspec §14: "Is there a translation? What remains missing?"

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.db import store

USER_AGENT = "patala-download/1.0 (mailto:dev@patala.local)"
SCHOLARLY_AUTHORS = ("lakshmanjoo", "jaideva", "dyczkowski", "hughes", "sands", "silburn",
                     "singh", "muktananda", "pradipaka", "vasugupta")
UNVERIFIED_TITLE = re.compile(r"\b(ai|hypertuned|auto)\b", re.I)
LADDER = ("DISCOVERED", "CATALOG_MATCHED", "DOWNLOAD_CONFIRMED", "TEXT_EXTRACTED", "SCHOLAR_CONFIRMED")


def _get_json(url: str, timeout: int = 25) -> dict:
    try:
        r = subprocess.run(["curl", "-s", "-m", str(timeout), "-A", USER_AGENT, url],
                           capture_output=True, text=True, timeout=timeout + 5)
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}


def _head_ok(url: str, timeout: int = 20) -> bool:
    """Live HEAD: does the download URL actually respond 200?"""
    try:
        r = subprocess.run(["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{http_code}",
                            "-I", "-m", str(timeout), "-A", USER_AGENT, url],
                           capture_output=True, text=True, timeout=timeout + 5)
        return r.stdout.strip() == "200"
    except Exception:
        return False


def confirm_archive(identifier: str, live: bool = True) -> dict:
    """Probe archive.org item → downloadable formats + tier + live confirmation."""
    m = _get_json(f"https://archive.org/metadata/{identifier}")
    files = m.get("files", [])
    formats = []
    total = 0
    for f in files:
        n = f.get("name", "")
        try:
            size = int(f.get("size", 0))
        except (TypeError, ValueError):
            size = 0
        if "_djvu.txt" in n:
            formats.append({"name": n, "kind": "ocr_text", "bytes": size})
            total += size
        elif "_text.pdf" in n or n.endswith(".pdf"):
            formats.append({"name": n, "kind": "pdf", "bytes": size})
            total += size

    downloadable = bool(formats)
    title = m.get("metadata", {}).get("title", "")
    tier = "C" if UNVERIFIED_TITLE.search(str(title)) else "B"

    live_confirmed = False
    if downloadable and live and formats:
        pick = formats[0]
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


def confirm_openlibrary(edition_key: str) -> dict:
    """Check OpenLibrary ebook_access for download availability."""
    if not edition_key:
        return {"downloadable": False, "tier": "C", "authority": "DISCOVERED"}

    d = _get_json(f"https://openlibrary.org/works/{edition_key}.json")
    access = d.get("ebook_access", "no_ebook")
    downloadable = access in ("public", "borrowable")
    tier = "A" if downloadable and any(a in str(d.get("title", "")).lower() for a in SCHOLARLY_AUTHORS) else "B"

    return {
        "source": "openlibrary", "edition_key": edition_key,
        "downloadable": downloadable, "ebook_access": access, "tier": tier,
        "authority": "DOWNLOAD_CONFIRMED" if downloadable else "CATALOG_MATCHED",
    }


def enrich_translation(hit: dict, live: bool = True) -> dict:
    """Enrich a translation hit with download verification + tier + evidence ladder."""
    source = hit.get("source", "")

    if source == "archive.org":
        result = confirm_archive(hit.get("identifier", ""), live=live)
    elif source == "openlibrary":
        result = confirm_openlibrary(hit.get("edition_key", ""))
    else:
        result = {"downloadable": False, "tier": "C", "authority": "DISCOVERED"}

    # Merge
    hit.update(result)
    hit["evidence_ladder"] = LADDER[LADDER.index(result.get("authority", "DISCOVERED"))]
    return hit
