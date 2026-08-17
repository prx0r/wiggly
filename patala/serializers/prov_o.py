#!/usr/bin/env python3
"""patala/serializers/prov_o.py — PROV-O ontology serializer.

Exports Pāṭala provenance as PROV-O compatible JSON-LD.
Spec: https://www.w3.org/TR/prov-o/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import time
from typing import Any


def serialize_derivation_activity(activity: dict) -> dict:
    """Convert a Pāṭala DerivationActivity to PROV-O JSON-LD."""
    prov = {
        "@context": "http://www.w3.org/ns/prov.jsonld",
        "type": "prov:Activity",
        "id": activity.get("id", ""),
        "prov:startedAtTime": activity.get("started_at", ""),
        "prov:endedAtTime": activity.get("completed_at", ""),
    }

    # Inputs → prov:used
    for inp in activity.get("inputs", []):
        prov.setdefault("prov:used", []).append({
            "type": "prov:Entity",
            "id": inp.get("object_id", ""),
        })

    # Outputs → prov:wasGeneratedBy (reverse)
    for out in activity.get("outputs", []):
        prov.setdefault("prov:generated", []).append({
            "type": "prov:Entity",
            "id": out.get("object_id", ""),
        })

    # Actor → prov:wasAssociatedWith
    if activity.get("actor_id"):
        prov["prov:wasAssociatedWith"] = {
            "type": "prov:Agent",
            "id": activity["actor_id"],
        }

    # Software → prov:used (implementation)
    if activity.get("software"):
        prov.setdefault("prov:used", []).append({
            "type": "prov:SoftwareAgent",
            "id": activity["software"].get("name", ""),
            "prov:wasAttributedTo": activity["software"].get("version", ""),
        })

    return prov


def serialize_entity(entity_id: str, entity_type: str = "prov:Entity") -> dict:
    """Create a PROV-O entity statement."""
    return {
        "@context": "http://www.w3.org/ns/prov.jsonld",
        "type": entity_type,
        "id": entity_id,
    }


def serialize_agent(agent_id: str, agent_type: str = "prov:Agent") -> dict:
    """Create a PROV-O agent statement."""
    return {
        "@context": "http://www.w3.org/ns/prov.jsonld",
        "type": agent_type,
        "id": agent_id,
    }


def serialize_derivation_graph(entities: list[dict], activities: list[dict],
                                agents: list[dict]) -> dict:
    """Serialize a complete PROV-O derivation graph."""
    graph = {
        "@context": "http://www.w3.org/ns/prov.jsonld",
        "type": "prov:Bundle",
        "entities": [serialize_entity(e["id"], e.get("type", "prov:Entity")) for e in entities],
        "activities": [serialize_derivation_activity(a) for a in activities],
        "agents": [serialize_agent(a["id"], a.get("type", "prov:Agent")) for a in agents],
    }
    return graph
