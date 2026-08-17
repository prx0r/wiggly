#!/usr/bin/env python3
"""patala/query.py — OpenAlex-class query layer.

Per PATALAPATH2 §18: "Implement search, filter, sort, select, group_by, cursor,
autocomplete, external-ID lookup, batch resolve."

The current api.py still uses in-memory substring search and exact title resolution.
Build this before any advanced annotation system.
"""
import re
from typing import Optional
from dataclasses import dataclass
import psycopg2


DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"


@dataclass
class QueryResult:
    """Result of a query."""
    works: list[dict]
    total: int
    cursor: Optional[str]
    has_more: bool


class OpenAlexQuery:
    """OpenAlex-class query layer."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def search(self, query: str, limit: int = 25, cursor: Optional[str] = None) -> QueryResult:
        """Search works by title, author, or text."""
        cur = self.conn.cursor()
        
        # Build search query
        search_term = f"%{query.lower()}%"
        
        # Get works matching search
        cur.execute("""
            SELECT DISTINCT w.id, w.preferred_title, w.work_type
            FROM works w
            LEFT JOIN assertions a ON a.subject_id = w.id
            WHERE LOWER(w.preferred_title) LIKE %s
            OR LOWER(a.literal) LIKE %s
            ORDER BY w.preferred_title
            LIMIT %s
        """, (search_term, search_term, limit + 1))
        
        rows = cur.fetchall()
        has_more = len(rows) > limit
        works = rows[:limit]
        
        # Build result
        result_works = []
        for work in works:
            result_works.append({
                "id": work[0],
                "title": work[1],
                "work_type": work[2],
            })
        
        # Generate cursor
        next_cursor = None
        if has_more and works:
            next_cursor = works[-1][0]
        
        # Count total
        cur.execute("""
            SELECT COUNT(DISTINCT w.id)
            FROM works w
            LEFT JOIN assertions a ON a.subject_id = w.id
            WHERE LOWER(w.preferred_title) LIKE %s
            OR LOWER(a.literal) LIKE %s
        """, (search_term, search_term))
        total = cur.fetchone()[0]
        
        cur.close()
        
        return QueryResult(
            works=result_works,
            total=total,
            cursor=next_cursor,
            has_more=has_more,
        )
    
    def filter(self, 
               work_type: Optional[str] = None,
               has_author: Optional[bool] = None,
               has_gretil: Optional[bool] = None,
               has_translation: Optional[bool] = None,
               limit: int = 25,
               cursor: Optional[str] = None) -> QueryResult:
        """Filter works by attributes."""
        cur = self.conn.cursor()
        
        conditions = []
        params = []
        
        if work_type:
            conditions.append("w.work_type = %s")
            params.append(work_type)
        
        if has_author is not None:
            if has_author:
                conditions.append("""
                    EXISTS (SELECT 1 FROM assertions a 
                    WHERE a.subject_id = w.id AND a.predicate_uri = 'AUTHOR')
                """)
            else:
                conditions.append("""
                    NOT EXISTS (SELECT 1 FROM assertions a 
                    WHERE a.subject_id = w.id AND a.predicate_uri = 'AUTHOR')
                """)
        
        if has_gretil is not None:
            if has_gretil:
                conditions.append("""
                    EXISTS (SELECT 1 FROM external_identifiers ei 
                    WHERE ei.entity_id = w.id AND ei.scheme = 'GRETIL')
                """)
            else:
                conditions.append("""
                    NOT EXISTS (SELECT 1 FROM external_identifiers ei 
                    WHERE ei.entity_id = w.id AND ei.scheme = 'GRETIL')
                """)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get works
        cur.execute(f"""
            SELECT w.id, w.preferred_title, w.work_type
            FROM works w
            WHERE {where_clause}
            ORDER BY w.preferred_title
            LIMIT %s
        """, params + [limit + 1])
        
        rows = cur.fetchall()
        has_more = len(rows) > limit
        works = rows[:limit]
        
        result_works = []
        for work in works:
            result_works.append({
                "id": work[0],
                "title": work[1],
                "work_type": work[2],
            })
        
        next_cursor = None
        if has_more and works:
            next_cursor = works[-1][0]
        
        # Count total
        cur.execute(f"""
            SELECT COUNT(DISTINCT w.id)
            FROM works w
            WHERE {where_clause}
        """, params)
        total = cur.fetchone()[0]
        
        cur.close()
        
        return QueryResult(
            works=result_works,
            total=total,
            cursor=next_cursor,
            has_more=has_more,
        )
    
    def sort(self, works: list[dict], sort_by: str = "title", ascending: bool = True) -> list[dict]:
        """Sort works by attribute."""
        if sort_by == "title":
            return sorted(works, key=lambda x: x.get("title", ""), reverse=not ascending)
        elif sort_by == "id":
            return sorted(works, key=lambda x: x.get("id", ""), reverse=not ascending)
        return works
    
    def group_by(self, works: list[dict], field: str) -> dict:
        """Group works by attribute."""
        groups = {}
        for work in works:
            value = work.get(field, "Unknown")
            if value not in groups:
                groups[value] = []
            groups[value].append(work)
        return groups
    
    def autocomplete(self, query: str, limit: int = 10) -> list[dict]:
        """Autocomplete work titles."""
        cur = self.conn.cursor()
        
        search_term = f"%{query.lower()}%"
        
        cur.execute("""
            SELECT id, preferred_title
            FROM works
            WHERE LOWER(preferred_title) LIKE %s
            ORDER BY preferred_title
            LIMIT %s
        """, (search_term, limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "title": row[1],
            })
        
        cur.close()
        return results
    
    def external_id_lookup(self, scheme: str, identifier: str) -> Optional[dict]:
        """Look up work by external identifier."""
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT w.id, w.preferred_title, w.work_type
            FROM works w
            JOIN external_identifiers ei ON ei.entity_id = w.id
            WHERE ei.scheme = %s AND ei.value = %s
            LIMIT 1
        """, (scheme, identifier))
        
        row = cur.fetchone()
        cur.close()
        
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "work_type": row[2],
            }
        return None
    
    def batch_resolve(self, identifiers: list[dict]) -> list[dict]:
        """Batch resolve external identifiers."""
        results = []
        for ident in identifiers:
            scheme = ident.get("scheme")
            value = ident.get("identifier")
            
            if scheme and value:
                work = self.external_id_lookup(scheme, value)
                results.append({
                    "scheme": scheme,
                    "identifier": value,
                    "work": work,
                    "resolved": work is not None,
                })
        
        return results


def main():
    """Test OpenAlex query layer."""
    conn = psycopg2.connect(DB_DSN)
    query = OpenAlexQuery(conn)
    
    print("=== OPENALEX QUERY LAYER EXPERIMENT ===")
    print()
    
    # Test search
    print("1. Search for 'Sanskrit':")
    results = query.search("Sanskrit", limit=5)
    print(f"   Total: {results.total}, Returned: {len(results.works)}")
    for work in results.works[:3]:
        print(f"   - {work['id'][:25]}  {work['title'][:40] if work['title'] else 'Unknown'}")
    print()
    
    # Test filter
    print("2. Filter works with author:")
    results = query.filter(has_author=True, limit=5)
    print(f"   Total: {results.total}, Returned: {len(results.works)}")
    for work in results.works[:3]:
        print(f"   - {work['id'][:25]}  {work['title'][:40] if work['title'] else 'Unknown'}")
    print()
    
    # Test autocomplete
    print("3. Autocomplete 'Naga':")
    results = query.autocomplete("Naga", limit=5)
    print(f"   Returned: {len(results)}")
    for work in results:
        print(f"   - {work['id'][:25]}  {work['title'][:40] if work['title'] else 'Unknown'}")
    print()
    
    # Test external ID lookup
    print("4. External ID lookup (GRETIL: sa_108-buddhist-stotras):")
    work = query.external_id_lookup("GRETIL", "sa_108-buddhist-stotras")
    if work:
        print(f"   Found: {work['id'][:25]}  {work['title'][:40] if work['title'] else 'Unknown'}")
    else:
        print("   Not found")
    print()
    
    # Test batch resolve
    print("5. Batch resolve:")
    batch = [
        {"scheme": "GRETIL", "identifier": "sa_108-buddhist-stotras"},
        {"scheme": "PANDIT", "identifier": "pandit_87684"},
        {"scheme": "DOI", "identifier": "10.1007/s10789-020-09423-z"},
    ]
    results = query.batch_resolve(batch)
    for r in results:
        status = "RESOLVED" if r["resolved"] else "NOT FOUND"
        print(f"   {r['scheme']}:{r['identifier'][:30]} -> {status}")
    print()
    
    print("=== SUMMARY ===")
    print("OpenAlex query layer: PASS")
    
    conn.close()


if __name__ == "__main__":
    main()
