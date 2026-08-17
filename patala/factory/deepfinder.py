#!/usr/bin/env python3
"""patala/factory/deepfinder.py — Translation deepfinder (Postgres-backed).

Finds ACTUAL translations from OpenLibrary, archive.org, Wisdomlib, etc.
Searches sources per work and returns translation-EDITION hits.

Per newbuildmainspec §14: "For any Sanskrit work, what exists? Where? In what form?
According to whom? How certain are we? Is there a translation?"

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from patala.db import store

USER_AGENT = "patala-deepfinder/1.0 (mailto:dev@patala.local)"
TRANS_LANGS = {"eng", "hin", "fre", "ger", "ita", "san+eng", "eng+san"}


def _norm(s: str) -> str:
    t = {'ā': 'a', 'ī': 'i', 'ū': 'u', 'ṛ': 'r', 'ṝ': 'r', 'ḷ': 'l', 'ḹ': 'l',
         'ṃ': 'm', 'ṁ': 'm', 'ñ': 'n', 'ṅ': 'n', 'ṇ': 'n', 'ś': 's', 'ṣ': 's',
         'ṭ': 't', 'ḍ': 'd', 'ḥ': 'h'}
    return re.sub(r'[^a-z0-9 ]', '', ''.join(t.get(c, c) for c in s.lower()))


def _get_json(url: str, params: dict | list | None = None, timeout: int = 25) -> dict:
    if params:
        if isinstance(params, dict):
            url = url + "?" + urllib.parse.urlencode(params, doseq=True)
        else:
            url = url + "?" + urllib.parse.urlencode(params)
    try:
        r = subprocess.run(["curl", "-s", "-m", str(timeout), "-A", USER_AGENT, url],
                           capture_output=True, text=True, timeout=timeout + 5)
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}


def openlibrary_search(title: str, limit: int = 5) -> list[dict]:
    """Search OpenLibrary for translation editions of a work."""
    work_tokens = {w for w in _norm(title).split() if len(w) >= 5}
    work_stripped = _norm(title).replace(" ", "")

    d = _get_json("https://openlibrary.org/search.json",
                  {"q": title, "limit": limit,
                   "fields": "title,author_name,language,ebook_access,publish_year,edition_key"})

    hits = []
    for x in d.get("docs", []):
        langs = x.get("language") or []
        langs_norm = {re.sub(r"[^a-z]", "", l.lower()) for l in langs}
        is_translation = bool(langs_norm & TRANS_LANGS)
        if not is_translation and "san" in langs_norm:
            continue

        res_title = _norm(x.get("title", ""))
        token_hit = any(tok in res_title for tok in work_tokens) if work_tokens else False
        stripped_hit = len(work_stripped) >= 8 and work_stripped in res_title.replace(" ", "")
        if work_tokens and not (token_hit or stripped_hit):
            continue

        hits.append({
            "source": "openlibrary",
            "title": x.get("title", ""),
            "author": (x.get("author_name") or [""])[0],
            "language": "en" if (langs_norm & {"eng"}) else "other",
            "year": (x.get("publish_year") or [None])[0],
            "is_translation": is_translation,
            "ebook_access": x.get("ebook_access"),
            "edition_key": (x.get("edition_key") or [""])[0],
        })
    return hits


def archive_search(title: str, rows: int = 6) -> list[dict]:
    """Search archive.org for translation-like items."""
    work_terms = _norm(title).split()
    core = " ".join(work_terms[:1])
    if len(core) < 4:
        return []

    d = _get_json("https://archive.org/advancedsearch.php",
                  [("q", f'"{core}" AND title:(translation OR english OR hindi OR french)'),
                   ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "language"),
                   ("rows", rows), ("output", "json")])

    hits = []
    for x in d.get("response", {}).get("docs", []):
        t = str(x.get("title", ""))
        raw_langs = x.get("language")
        langs = [str(l).lower().split("-")[0] for l in ([raw_langs] if isinstance(raw_langs, str) else list(raw_langs or []))]
        lang_signal = bool(set(langs) & {"eng", "fre", "hin", "ger", "ita", "spa"})
        if not lang_signal and not re.search(r"translation|english|hindi|french", t, re.I):
            continue
        if set(langs) & {"san", "sa"} and not re.search(r"translation|english", t, re.I):
            continue
        lang = "en" if "eng" in langs else "hi" if "hin" in langs else "fr" if "fre" in langs else "en"
        hits.append({
            "source": "archive.org", "identifier": x.get("identifier"), "title": t[:90],
            "is_translation": True, "language": lang,
            "url": f"https://archive.org/details/{x.get('identifier')}",
        })
    return hits


def find_translations_for_work(work_id: str, work_title: str) -> list[dict]:
    """Search all sources for translations of a work.

    Returns list of translation hits with source, title, language, confidence.
    """
    hits = []

    # OpenLibrary
    try:
        ol_hits = openlibrary_search(work_title, limit=5)
        hits.extend(ol_hits)
        time.sleep(0.5)
    except Exception:
        pass

    # Archive.org
    try:
        ar_hits = archive_search(work_title, rows=6)
        hits.extend(ar_hits)
        time.sleep(0.5)
    except Exception:
        pass

    # Deduplicate by title
    seen = set()
    unique = []
    for h in hits:
        key = _norm(h.get("title", ""))
        if key not in seen:
            seen.add(key)
            unique.append(h)

    return unique


def run_deepfind(work_id: str, work_title: str) -> dict:
    """Run deepfind for a work and return results with provenance."""
    hits = find_translations_for_work(work_id, work_title)

    # Record search event
    search_id = f"PTSE_{work_id}_deepfind"
    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO task_candidates (id, task_type, target_id, priority, reason, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (search_id, "SEARCH_TRANSLATION", work_id, 0.5,
          f"Deepfound {len(hits)} translation candidates for '{work_title}'",
          "COMPLETED"))
    conn.commit()
    cur.close()
    conn.close()

    return {
        "work_id": work_id,
        "work_title": work_title,
        "hits": hits,
        "hit_count": len(hits),
        "search_id": search_id,
    }
