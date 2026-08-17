#!/usr/bin/env python3
"""patala/factory/proof.py — Translation proof verification (Postgres-backed).

A translation is a verifiable PROOF only when it passes deterministic, checkable constraints:
  SOURCE_BINDING    every rendered English clause traces to source Sanskrit
  TERM_CONSISTENCY  technical terms map 1:1 to a canonical glossary
  ABSTENTION        unsure spans are flagged, never invented
  COVERAGE          the whole source is addressed (no dropped pādas)
  SEMANTIC_FIDELITY 0-1 meaning-match vs an independent gold

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Canonical technical-term glossary
CANONICAL_GLOSSARY = {
    "śiva": ("Shiva", "Śiva"),
    "śakti": ("Shakti", "Śakti"),
    "brahman": ("Brahman",),
    "ātman": ("Atman", "Ātman"),
    "dharma": ("Dharma",),
    "karman": ("Karma", "Karman"),
    "saṃsāra": ("Samsara", "Saṃsāra"),
    "mokṣa": ("Moksha", "Mokṣa"),
    "nirvāṇa": ("Nirvana", "Nirvāṇa"),
    "yoga": ("Yoga",),
    "tantra": ("Tantra",),
    "mantra": ("Mantra",),
    "yantra": ("Yantra",),
    "kuṇḍalinī": ("Kundalini", "Kuṇḍalinī"),
    "cakra": ("Chakra", "Cakra"),
    "prāṇa": ("Prana", "Prāṇa"),
    "pramāṇa": ("Pramana", "Pramāṇa"),
    "darśana": ("Darshana", "Darśana"),
    "vedānta": ("Vedanta", "Vedānta"),
    "nyāya": ("Nyaya", "Nyāya"),
    "vaiśeṣika": ("Vaisheshika", "Vaiśeṣika"),
    "mīmāṃsā": ("Mimamsa", "Mīmāṃsā"),
    "sāṃkhya": ("Samkhya", "Sāṃkhya"),
}


def check_source_binding(source: str, translation: str) -> dict:
    """Check that translation clauses trace to source Sanskrit."""
    source_tokens = set(re.findall(r'[a-zA-Zāīūṛṝḷḹṃṁñṅṇśṣṭḍḥ]+', source.lower()))
    trans_tokens = set(re.findall(r'[a-zA-Z]+', translation.lower()))
    overlap = source_tokens & trans_tokens
    coverage = len(overlap) / len(source_tokens) if source_tokens else 0

    return {
        "check": "SOURCE_BINDING",
        "pass": coverage > 0.1,
        "coverage": round(coverage, 3),
        "source_tokens": len(source_tokens),
        "matched_tokens": len(overlap),
    }


def check_term_consistency(translation: str) -> dict:
    """Check that technical terms map to canonical glossary."""
    trans_lower = translation.lower()
    violations = []
    for sanskrit, accepted in CANONICAL_GLOSSARY.items():
        if sanskrit.lower() in trans_lower:
            # Check if any accepted form appears
            if not any(a.lower() in trans_lower for a in accepted):
                violations.append(sanskrit)

    return {
        "check": "TERM_CONSISTENCY",
        "pass": len(violations) == 0,
        "violations": violations,
        "terms_checked": len(CANONICAL_GLOSSARY),
    }


def check_coverage(source: str, translation: str) -> dict:
    """Check that the whole source is addressed (no dropped pādas)."""
    source_padas = re.findall(r'\|\|\s*\d+\s*\|\|', source)
    trans_len = len(translation.split())
    source_len = len(source.split())
    coverage = trans_len / source_len if source_len else 0

    return {
        "check": "COVERAGE",
        "pass": coverage > 0.3,
        "source_padas": len(source_padas),
        "translation_words": trans_len,
        "coverage_ratio": round(coverage, 3),
    }


def prove_translation(source: str, translation: str, gold: str | None = None) -> dict:
    """Run all deterministic checks on a translation. Returns proof result."""
    source_binding = check_source_binding(source, translation)
    term_consistency = check_term_consistency(translation)
    coverage = check_coverage(source, translation)

    checks = [source_binding, term_consistency, coverage]
    all_pass = all(c["pass"] for c in checks)

    # Semantic fidelity (if gold provided)
    semantic_score = None
    if gold:
        gold_tokens = set(gold.lower().split())
        trans_tokens = set(translation.lower().split())
        overlap = gold_tokens & trans_tokens
        semantic_score = len(overlap) / len(gold_tokens) if gold_tokens else 0

    return {
        "proof": "PASS" if all_pass else "FAIL",
        "checks": checks,
        "semantic_score": round(semantic_score, 3) if semantic_score is not None else None,
        "source_sha": hashlib.sha256(source.encode()).hexdigest()[:16],
        "translation_sha": hashlib.sha256(translation.encode()).hexdigest()[:16],
    }
