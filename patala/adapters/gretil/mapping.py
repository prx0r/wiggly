#!/usr/bin/env python3
"""GRETIL adapter — extraction rules for mapping TEI fields to assertions."""
from __future__ import annotations

EXTRACTION_RULES = [
    {
        "predicate": "TITLE",
        "xpath": ".//tei:titleStmt/tei:title",
        "method": "XML_PATH",
    },
    {
        "predicate": "AUTHOR",
        "xpath": ".//tei:titleStmt/tei:author",
        "method": "XML_PATH",
    },
    {
        "predicate": "LANGUAGE",
        "xpath": ".//tei:langUsage/tei:language/@ident",
        "method": "XML_PATH",
    },
    {
        "predicate": "DATE",
        "xpath": ".//tei:publicationStmt/tei:date/@when-iso",
        "method": "XML_PATH",
    },
]
