#!/usr/bin/env python3
"""Re-ingest GRETIL data."""
import asyncio
import sys
import psycopg2
from datetime import datetime, timezone

sys.path.insert(0, '/root/openpatalanew')

from patala.adapters.gretil.adapter import GretilAdapter

DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"


async def reingest_gretil():
    """Re-ingest GRETIL data."""
    adapter = GretilAdapter()
    
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    
    print("=== RE-INGESTING GRETIL DATA ===")
    print()
    
    # Get GRETIL entities
    result = await adapter.discover(limit=100)
    items = result['items']
    print(f"Found {len(items)} GRETIL entities")
    print()
    
    # Process each entity
    for i, item in enumerate(items, 1):
        # Fetch metadata
        obs = await adapter.fetch_metadata(item)
        
        # Normalize
        bundle = await adapter.normalize(obs)
        
        # Write to database
        for candidate in bundle['entity_candidates']:
            # Check if work exists
            cur.execute('''
                SELECT id FROM works WHERE id = %s
            ''', (candidate['id'],))
            exists = cur.fetchone()
            
            if not exists:
                # Create work
                cur.execute('''
                    INSERT INTO works (id, preferred_title, work_type, created_at, schema_uri)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (
                    candidate['id'],
                    item.get('title', ''),
                    'TEXT',
                    datetime.now(timezone.utc),
                    'https://patala.org/schemas/v2/work.json',
                ))
            
            # Write assertions
            for assertion in bundle['assertions']:
                # Check if assertion exists
                cur.execute('''
                    SELECT id FROM assertions WHERE id = %s
                ''', (assertion['id'],))
                exists = cur.fetchone()
                
                if not exists:
                    cur.execute('''
                        INSERT INTO assertions (id, subject_id, predicate_uri, literal, epistemic_mode, evidence_use_ids, asserted_by, recorded_at, lifecycle, created_from_event, schema_uri)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        assertion['id'],
                        candidate['id'],
                        assertion['predicate'],
                        assertion['value'],
                        'observed',
                        '{}',
                        'PROVIDER',
                        datetime.now(timezone.utc),
                        'ACTIVE',
                        'PTEVT_reingest',
                        'https://patala.org/schemas/v2/assertion.json',
                    ))
            
            # Write external IDs
            for ext_id in bundle['external_ids']:
                # Check if ext_id exists
                cur.execute('''
                    SELECT id FROM external_identifiers WHERE id = %s
                ''', (ext_id['id'],))
                exists = cur.fetchone()
                
                if not exists:
                    cur.execute('''
                        INSERT INTO external_identifiers (id, entity_id, scheme, value, source_observation_id, relation_confidence, created_at, schema_uri)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        ext_id['id'],
                        candidate['id'],
                        ext_id['scheme'],
                        ext_id['value'],
                        ext_id['source_observation_id'],
                        ext_id['relation_confidence'],
                        datetime.now(timezone.utc),
                        'https://patala.org/schemas/v2/external-identifier.json',
                    ))
        
        if i % 20 == 0:
            print(f"  [{i:3d}/{len(items)}] Processed")
            conn.commit()
    
    conn.commit()
    
    # Summary
    cur.execute('SELECT COUNT(*) FROM works')
    works_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM assertions')
    assertions_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM external_identifiers')
    ext_ids_count = cur.fetchone()[0]
    
    print()
    print("=== SUMMARY ===")
    print(f"Works: {works_count}")
    print(f"Assertions: {assertions_count}")
    print(f"External IDs: {ext_ids_count}")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(reingest_gretil())
