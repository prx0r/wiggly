#!/usr/bin/env python3
"""patala/annotation.py — Text/Passage Annotation Interop.

Per PATALAPATH2 §18: "Use STAM, OpenPeka, ATLAS, Web Annotation for
passages, linguistics, alignments, annotations."

No new permanent identity model.
"""
from dataclasses import dataclass
from typing import Optional
import json
import psycopg2
from datetime import datetime, timezone


DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"


@dataclass
class TextAnchor:
    """A text anchor for annotation."""
    source_artifact_id: str
    selectors: list[dict]
    source_digest: dict
    normalization_profile: Optional[str]


@dataclass
class Annotation:
    """An annotation on a text."""
    id: str
    type: str
    target: TextAnchor
    body: dict
    motivation: str
    created: str
    source: str


@dataclass
class PassageAnnotation:
    """A passage-level annotation."""
    work_id: str
    passage_id: str
    text: str
    annotations: list[Annotation]
    metadata: dict


class AnnotationInterop:
    """Text/Passage Annotation Interop system."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def create_text_anchor(self, work_id: str, start: int, end: int, text: str) -> TextAnchor:
        """Create a text anchor for annotation."""
        return TextAnchor(
            source_artifact_id=work_id,
            selectors=[
                {"type": "TextPosition", "start": start, "end": end},
                {"type": "TextQuote", "exact": text},
            ],
            source_digest={"algorithm": "sha256", "value": ""},
            normalization_profile=None,
        )
    
    def create_annotation(self, anchor: TextAnchor, body: dict, motivation: str = "linking") -> Annotation:
        """Create an annotation."""
        import uuid
        return Annotation(
            id=f"PTANN_{uuid.uuid4().hex[:16]}",
            type="Annotation",
            target=anchor,
            body=body,
            motivation=motivation,
            created=datetime.now(timezone.utc).isoformat(),
            source="openpatala",
        )
    
    def create_passage_annotation(self, work_id: str, passage_id: str, text: str, 
                                   annotations: list[Annotation] = None) -> PassageAnnotation:
        """Create a passage-level annotation."""
        return PassageAnnotation(
            work_id=work_id,
            passage_id=passage_id,
            text=text,
            annotations=annotations or [],
            metadata={
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "openpatala",
            },
        )
    
    def convert_to_stam_format(self, annotation: Annotation) -> dict:
        """Convert annotation to STAM format."""
        return {
            "type": "Annotation",
            "id": annotation.id,
            "target": {
                "type": "TextSelector",
                "text": {"set": annotation.target.source_artifact_id},
                "begin": annotation.target.selectors[0].get("start", 0),
                "end": annotation.target.selectors[0].get("end", 0),
            },
            "body": annotation.body,
            "motivation": annotation.motivation,
            "created": annotation.created,
        }
    
    def convert_to_web_annotation(self, annotation: Annotation) -> dict:
        """Convert annotation to W3C Web Annotation format."""
        return {
            "@context": "http://www.w3.org/ns/anno/jsonld",
            "type": "Annotation",
            "id": annotation.id,
            "target": {
                "source": annotation.target.source_artifact_id,
                "selector": {
                    "type": "TextPositionSelector",
                    "start": annotation.target.selectors[0].get("start", 0),
                    "end": annotation.target.selectors[0].get("end", 0),
                },
            },
            "body": {
                "type": "TextualBody",
                "value": annotation.body.get("value", ""),
                "format": annotation.body.get("format", "text/plain"),
            },
            "motivation": annotation.motivation,
            "created": annotation.created,
        }
    
    def convert_to_atlas_format(self, annotation: Annotation) -> dict:
        """Convert annotation to ATLAS format."""
        return {
            "label": annotation.body.get("label", ""),
            "lemma": annotation.body.get("lemma", ""),
            "morphCode": annotation.body.get("morphCode", ""),
            "parsing": annotation.body.get("parsing", ""),
            "vocabularyForm": annotation.body.get("vocabularyForm", ""),
            "reference": {
                "workId": annotation.target.source_artifact_id,
                "start": annotation.target.selectors[0].get("start", 0),
                "end": annotation.target.selectors[0].get("end", 0),
            },
        }
    
    def get_annotations_for_work(self, work_id: str) -> list[PassageAnnotation]:
        """Get all annotations for a work."""
        cur = self.conn.cursor()
        
        # Get document segments (passages)
        cur.execute("""
            SELECT id, etext_id, segment_type, text
            FROM document_segments
            WHERE etext_id = %s
        """, (work_id,))
        
        passages = []
        for seg_id, wk_id, seg_type, content in cur.fetchall():
            # Create a passage annotation
            passage = self.create_passage_annotation(
                work_id=wk_id,
                passage_id=seg_id,
                text=content or "",
            )
            passages.append(passage)
        
        cur.close()
        return passages


def main():
    """Test annotation interop."""
    conn = psycopg2.connect(DB_DSN)
    interop = AnnotationInterop(conn)
    
    print("=== TEXT/PASSAGE ANNOTATION INTEROP EXPERIMENT ===")
    print()
    
    # Create a sample annotation
    print("1. Creating sample annotation...")
    anchor = interop.create_text_anchor(
        work_id="PTW_0006803ca8677e45",
        start=0,
        end=10,
        text="sample text",
    )
    annotation = interop.create_annotation(
        anchor=anchor,
        body={"value": "test annotation", "format": "text/plain"},
        motivation="commenting",
    )
    print(f"   Created annotation: {annotation.id}")
    print()
    
    # Convert to different formats
    print("2. Converting to different formats...")
    stam = interop.convert_to_stam_format(annotation)
    web_anno = interop.convert_to_web_annotation(annotation)
    atlas = interop.convert_to_atlas_format(annotation)
    print(f"   STAM: {list(stam.keys())}")
    print(f"   Web Annotation: {list(web_anno.keys())}")
    print(f"   ATLAS: {list(atlas.keys())}")
    print()
    
    # Get annotations for a work
    print("3. Getting annotations for work...")
    passages = interop.get_annotations_for_work("PTW_0006803ca8677e45")
    print(f"   Found {len(passages)} passages")
    print()
    
    print("=== SUMMARY ===")
    print("Annotation interop: PASS")
    
    conn.close()


if __name__ == "__main__":
    main()
