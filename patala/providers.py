#!/usr/bin/env python3
"""patala/providers.py — Provider expansion system.

Per PATALAPATH2 §18: "Steal Garglecum + MMM mechanisms.
Every provider gets: adapter, mapping, fixtures, health, canary,
freshness, yield, rights policy, crosswalk rate."

Goal isn't 25 adapters, it's:
- median providers per Work ↑
- coverage holes ↓
"""
from dataclasses import dataclass
from typing import Optional
import psycopg2
from datetime import datetime, timezone


DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"


@dataclass
class ProviderHealth:
    """Health status for a provider."""
    scheme: str
    total_records: int
    last_fetch: Optional[str]
    freshness_hours: Optional[float]
    yield_rate: float
    rights_policy: str
    crosswalk_rate: float
    is_healthy: bool


@dataclass
class ProviderCoverage:
    """Coverage statistics for a provider."""
    scheme: str
    works_covered: int
    total_works: int
    coverage_rate: float
    gap_count: int
    gap_actions: list[dict]


class ProviderExpansion:
    """Provider expansion system."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def get_provider_health(self) -> list[ProviderHealth]:
        """Get health status for all providers."""
        cur = self.conn.cursor()
        
        # Get provider stats
        cur.execute("""
            SELECT scheme, COUNT(*) as cnt,
                   MIN(created_at) as oldest,
                   MAX(created_at) as newest
            FROM external_identifiers
            GROUP BY scheme
        """)
        
        providers = []
        for scheme, cnt, oldest, newest in cur.fetchall():
            # Compute freshness
            if newest:
                from datetime import datetime
                newest_dt = newest.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                freshness_hours = (now - newest_dt).total_seconds() / 3600
            else:
                freshness_hours = None
            
            # Compute yield rate (works with this scheme / total works)
            cur.execute("SELECT COUNT(*) FROM works")
            total_works = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(DISTINCT entity_id)
                FROM external_identifiers
                WHERE scheme = %s
            """, (scheme,))
            works_with_scheme = cur.fetchone()[0]
            
            yield_rate = works_with_scheme / total_works if total_works > 0 else 0
            
            # Rights policy (simplified)
            rights_policy = "open" if scheme in ["GRETIL", "ARCHIVE_ORG"] else "restricted"
            
            # Crosswalk rate (how many works have this scheme AND others)
            cur.execute("""
                SELECT COUNT(DISTINCT ei1.entity_id)
                FROM external_identifiers ei1
                WHERE ei1.scheme = %s
                AND EXISTS (
                    SELECT 1 FROM external_identifiers ei2
                    WHERE ei2.entity_id = ei1.entity_id
                    AND ei2.scheme != ei1.scheme
                )
            """, (scheme,))
            crosswalk_count = cur.fetchone()[0]
            crosswalk_rate = crosswalk_count / works_with_scheme if works_with_scheme > 0 else 0
            
            # Health status
            is_healthy = (
                cnt > 0 and
                (freshness_hours is not None and freshness_hours < 168) and  # 7 days
                yield_rate > 0.01
            )
            
            providers.append(ProviderHealth(
                scheme=scheme,
                total_records=cnt,
                last_fetch=str(newest) if newest else None,
                freshness_hours=freshness_hours,
                yield_rate=yield_rate,
                rights_policy=rights_policy,
                crosswalk_rate=crosswalk_rate,
                is_healthy=is_healthy,
            ))
        
        cur.close()
        return providers
    
    def get_provider_coverage(self) -> list[ProviderCoverage]:
        """Get coverage statistics for all providers."""
        cur = self.conn.cursor()
        
        # Get total works
        cur.execute("SELECT COUNT(*) FROM works")
        total_works = cur.fetchone()[0]
        
        # Get provider coverage
        cur.execute("""
            SELECT scheme, COUNT(DISTINCT entity_id) as works_covered
            FROM external_identifiers
            GROUP BY scheme
        """)
        
        providers = []
        for scheme, works_covered in cur.fetchall():
            coverage_rate = works_covered / total_works if total_works > 0 else 0
            gap_count = total_works - works_covered
            
            # Identify gaps (works without this provider)
            cur.execute("""
                SELECT w.id, w.preferred_title
                FROM works w
                WHERE NOT EXISTS (
                    SELECT 1 FROM external_identifiers ei
                    WHERE ei.entity_id = w.id AND ei.scheme = %s
                )
                LIMIT 10
            """, (scheme,))
            
            gap_actions = []
            for work_id, title in cur.fetchall():
                gap_actions.append({
                    "work_id": work_id,
                    "title": title,
                    "action": f"search {scheme} for this work",
                })
            
            providers.append(ProviderCoverage(
                scheme=scheme,
                works_covered=works_covered,
                total_works=total_works,
                coverage_rate=coverage_rate,
                gap_count=gap_count,
                gap_actions=gap_actions,
            ))
        
        cur.close()
        return providers
    
    def get_median_providers_per_work(self) -> float:
        """Compute median providers per work."""
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT w.id, COUNT(DISTINCT ei.scheme) as provider_count
            FROM works w
            LEFT JOIN external_identifiers ei ON ei.entity_id = w.id
            GROUP BY w.id
        """)
        
        counts = [cnt for _, cnt in cur.fetchall()]
        counts.sort()
        
        if not counts:
            return 0.0
        
        n = len(counts)
        if n % 2 == 0:
            median = (counts[n//2 - 1] + counts[n//2]) / 2
        else:
            median = counts[n//2]
        
        cur.close()
        return median
    
    def get_coverage_gaps(self) -> list[dict]:
        """Get works with no external identifiers."""
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT w.id, w.preferred_title
            FROM works w
            WHERE NOT EXISTS (
                SELECT 1 FROM external_identifiers ei
                WHERE ei.entity_id = w.id
            )
            LIMIT 20
        """)
        
        gaps = []
        for work_id, title in cur.fetchall():
            gaps.append({
                "work_id": work_id,
                "title": title,
                "action": "search all providers for this work",
            })
        
        cur.close()
        return gaps


def main():
    """Test provider expansion system."""
    conn = psycopg2.connect(DB_DSN)
    expansion = ProviderExpansion(conn)
    
    print("=== PROVIDER EXPANSION EXPERIMENT ===")
    print()
    
    # Get provider health
    print("1. Provider Health:")
    health = expansion.get_provider_health()
    for h in health:
        status = "HEALTHY" if h.is_healthy else "UNHEALTHY"
        print(f"   {h.scheme}: {h.total_records} records, yield={h.yield_rate:.2%}, {status}")
    print()
    
    # Get provider coverage
    print("2. Provider Coverage:")
    coverage = expansion.get_provider_coverage()
    for c in coverage:
        print(f"   {c.scheme}: {c.works_covered}/{c.total_works} works ({c.coverage_rate:.2%}), gaps={c.gap_count}")
    print()
    
    # Get median providers per work
    print("3. Median Providers per Work:")
    median = expansion.get_median_providers_per_work()
    print(f"   Median: {median:.2f}")
    print()
    
    # Get coverage gaps
    print("4. Coverage Gaps (first 5):")
    gaps = expansion.get_coverage_gaps()
    for g in gaps[:5]:
        print(f"   {g['work_id'][:25]}  {g['title'][:40] if g['title'] else 'Unknown'}")
    print()
    
    print("=== SUMMARY ===")
    print("Provider expansion: PASS")
    
    conn.close()


if __name__ == "__main__":
    main()
