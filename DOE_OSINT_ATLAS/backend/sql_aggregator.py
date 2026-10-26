"""SQL aggregation path for intent=aggregate queries.

Vector RAG returns top-k chunks. SQL returns GROUP BY rollups. The user's
question 'who has contracts for nuclear waste' needs SUM(obligation) and
COUNT(*) over potentially hundreds of matching rows — vector retrieval can't
do that. This module is the aggregate path.
"""
import sqlite3
from dataclasses import dataclass, field


@dataclass
class ContractorRollup:
    recipient_name: str
    contract_count: int
    total_obligation: float
    fiscal_years: list[int] = field(default_factory=list)
    top_psc: list[str] = field(default_factory=list)
    top_naics: list[str] = field(default_factory=list)
    sample_descriptions: list[str] = field(default_factory=list)


def aggregate_contracts(
    db_path: str,
    search_terms: list[str],
    filters: dict,
    limit: int = 20,
) -> list[ContractorRollup]:
    """GROUP BY recipient_name aggregation matching search_terms + filters.

    Args:
        db_path: path to doe_contracts.db
        search_terms: list of terms to LIKE-match against description, PSC, NAICS
        filters: optional {"state": str, "fiscal_year": int, "min_obligation": float}
        limit: max number of rollups to return (default 20)

    Returns:
        List of ContractorRollup, sorted by total_obligation DESC.
        Empty list if no matches.
    """
    if not search_terms:
        return []

    where_parts: list[str] = []
    params: list = []

    # Search terms: each term must match in description, PSC, or NAICS
    # All terms ANDed (e.g., "nuclear waste" requires both nuclear AND waste)
    for term in search_terms:
        where_parts.append(
            "(transaction_description LIKE ? "
            "OR product_or_service_code_description LIKE ? "
            "OR naics_description LIKE ?)"
        )
        wildcard = f"%{term}%"
        params.extend([wildcard, wildcard, wildcard])

    # Filters
    if filters.get("state"):
        where_parts.append("recipient_state_name = ?")
        params.append(filters["state"])
    if filters.get("fiscal_year"):
        where_parts.append("action_date_fiscal_year = ?")
        params.append(filters["fiscal_year"])
    if filters.get("min_obligation"):
        where_parts.append("federal_action_obligation >= ?")
        params.append(filters["min_obligation"])

    where_clause = " AND ".join(where_parts) if where_parts else "1=1"

    sql = f"""
        SELECT
            recipient_name,
            COUNT(*) as contract_count,
            SUM(federal_action_obligation) as total_obligation,
            GROUP_CONCAT(DISTINCT action_date_fiscal_year) as years,
            GROUP_CONCAT(DISTINCT product_or_service_code_description) as pscs,
            GROUP_CONCAT(DISTINCT naics_description) as naics_list
        FROM contracts
        WHERE {where_clause}
            AND recipient_name IS NOT NULL
            AND federal_action_obligation IS NOT NULL
        GROUP BY recipient_name
        ORDER BY total_obligation DESC
        LIMIT ?
    """
    params.append(limit)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()

    # Fetch sample descriptions per recipient (3 each) — separate query to keep
    # the GROUP BY clean
    rollups: list[ContractorRollup] = []
    for row in rows:
        sample_sql = f"""
            SELECT transaction_description
            FROM contracts
            WHERE recipient_name = ? AND ({where_clause})
            ORDER BY federal_action_obligation DESC
            LIMIT 3
        """
        sample_params = [row["recipient_name"]] + params[:-1]  # exclude limit
        samples = conn.execute(sample_sql, sample_params).fetchall()

        rollups.append(ContractorRollup(
            recipient_name=row["recipient_name"],
            contract_count=row["contract_count"],
            total_obligation=row["total_obligation"] or 0.0,
            fiscal_years=sorted(int(y) for y in (row["years"] or "").split(",") if y),
            top_psc=[p for p in (row["pscs"] or "").split(",")[:3] if p],
            top_naics=[n for n in (row["naics_list"] or "").split(",")[:3] if n],
            sample_descriptions=[s["transaction_description"] for s in samples if s["transaction_description"]],
        ))

    conn.close()
    return rollups
