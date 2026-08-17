#!/usr/bin/env python3
"""patala/serializers/cidoc_crm.py — CIDOC CRM export serializer.

Maps Pāṭala entities to CIDOC CRM / CRMinf / CRMsci RDF for cultural heritage interoperability.
Spec: https://cidoc-crm.org/

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import time
from typing import Any


def serialize_work(work: dict, assertions: list[dict] = None) -> dict:
    """Map a Pāṭala Work to CIDOC CRM E21 Person / E31 Documentary Object.

    CRMinf maps assertions to argumentation/inference.
    """
    crm = {
        "@context": "https://cidoc-crm.org/7.1.1/",
        "type": "crm:E31_Documentary_Object",
        "id": work.get("id", ""),
        "crm:P102_has_title": work.get("preferred_title", ""),
    }

    if assertions:
        crm["crm:P106_is_composed_of"] = []
        for a in (assertions or []):
            if a.get("predicate_uri", "").endswith("AUTHOR"):
                crm["crm:P106_is_composed_of"].append({
                    "type": "crm:E39_Actor",
                    "crm:P102_has_title": a.get("literal", ""),
                })

    return crm


def serialize_activity(activity: dict) -> dict:
    """Map a Pāṭala DerivationActivity to CIDOC CRM E5 Event."""
    return {
        "@context": "https://cidoc-crm.org/7.1.1/",
        "type": "crm:E5_Event",
        "id": activity.get("id", ""),
        "crm:P1_has_type": activity.get("activity_type", ""),
        "crm:P4_has_time_span": {
            "crm:P82_at_some_time_within": activity.get("started_at", ""),
        },
    }


def serialize_observation(observation: dict) -> dict:
    """Map a Pāṭala RawObservation to CRMsci Observation."""
    return {
        "@context": "https://cidoc-crm.org/7.1.1/",
        "type": "crmsci:O2_Observation",
        "id": observation.get("id", ""),
        "crm:P10_was_used_by": observation.get("provider_id", ""),
        "crm:P4_has_time_span": {
            "crm:P82_at_some_time_within": observation.get("observed_at", ""),
        },
    }
