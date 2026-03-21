"""Build knowledge graph from SQLite contracts data."""
import sqlite3
import argparse
import json
import igraph as ig
import leidenalg

def build_graph(db_path: str, output_path: str, topics_db_path: str | None = None) -> dict:
    """Build igraph from contract aggregations. Returns stats dict."""
    conn = sqlite3.connect(db_path)

    # 1. Extract unique entities
    recipients = conn.execute(
        "SELECT DISTINCT recipient_name, recipient_state_name, recipient_city_name, "
        "SUM(federal_action_obligation) as total "
        "FROM contracts WHERE recipient_name IS NOT NULL "
        "GROUP BY recipient_name, recipient_state_name, recipient_city_name"
    ).fetchall()

    pscs = conn.execute(
        "SELECT DISTINCT product_or_service_code_description "
        "FROM contracts WHERE product_or_service_code_description IS NOT NULL"
    ).fetchall()

    naics = conn.execute(
        "SELECT DISTINCT naics_description "
        "FROM contracts WHERE naics_description IS NOT NULL"
    ).fetchall()

    # 2. Build node lists with type prefixes for unique IDs
    g = ig.Graph()
    node_map = {}  # name -> vertex index

    # Add recipient nodes
    for name, state, city, total in recipients:
        idx = g.vcount()
        g.add_vertices(1)
        g.vs[idx]["name"] = f"recipient:{name}"
        g.vs[idx]["label"] = name
        g.vs[idx]["type"] = "recipient"
        g.vs[idx]["state"] = state
        g.vs[idx]["city"] = city
        g.vs[idx]["total_obligated"] = total or 0
        node_map[f"recipient:{name}"] = idx

    # Add PSC nodes
    for (desc,) in pscs:
        idx = g.vcount()
        g.add_vertices(1)
        g.vs[idx]["name"] = f"psc:{desc}"
        g.vs[idx]["label"] = desc
        g.vs[idx]["type"] = "psc"
        node_map[f"psc:{desc}"] = idx

    # Add NAICS nodes
    for (desc,) in naics:
        idx = g.vcount()
        g.add_vertices(1)
        g.vs[idx]["name"] = f"naics:{desc}"
        g.vs[idx]["label"] = desc
        g.vs[idx]["type"] = "naics"
        node_map[f"naics:{desc}"] = idx

    # 3. Build edges from contract aggregations
    # Recipient <-> PSC
    r_psc = conn.execute(
        "SELECT recipient_name, product_or_service_code_description, "
        "SUM(federal_action_obligation), COUNT(*) "
        "FROM contracts "
        "WHERE recipient_name IS NOT NULL AND product_or_service_code_description IS NOT NULL "
        "GROUP BY recipient_name, product_or_service_code_description"
    ).fetchall()

    edges = []
    weights = []
    edge_types = []
    contract_counts = []

    for rname, psc_desc, total_dollars, count in r_psc:
        src = node_map.get(f"recipient:{rname}")
        tgt = node_map.get(f"psc:{psc_desc}")
        if src is not None and tgt is not None:
            edges.append((src, tgt))
            weights.append(abs(total_dollars or 0))
            edge_types.append("recipient_psc")
            contract_counts.append(count)

    # Recipient <-> NAICS
    r_naics = conn.execute(
        "SELECT recipient_name, naics_description, "
        "SUM(federal_action_obligation), COUNT(*) "
        "FROM contracts "
        "WHERE recipient_name IS NOT NULL AND naics_description IS NOT NULL "
        "GROUP BY recipient_name, naics_description"
    ).fetchall()

    for rname, naics_desc, total_dollars, count in r_naics:
        src = node_map.get(f"recipient:{rname}")
        tgt = node_map.get(f"naics:{naics_desc}")
        if src is not None and tgt is not None:
            edges.append((src, tgt))
            weights.append(abs(total_dollars or 0))
            edge_types.append("recipient_naics")
            contract_counts.append(count)

    # PSC <-> NAICS co-occurrence
    psc_naics = conn.execute(
        "SELECT product_or_service_code_description, naics_description, COUNT(*) "
        "FROM contracts "
        "WHERE product_or_service_code_description IS NOT NULL "
        "AND naics_description IS NOT NULL "
        "GROUP BY product_or_service_code_description, naics_description"
    ).fetchall()

    for psc_desc, naics_desc, count in psc_naics:
        src = node_map.get(f"psc:{psc_desc}")
        tgt = node_map.get(f"naics:{naics_desc}")
        if src is not None and tgt is not None:
            edges.append((src, tgt))
            weights.append(count)
            edge_types.append("psc_naics")
            contract_counts.append(count)

    conn.close()

    # 4. Add all edges
    g.add_edges(edges)
    g.es["weight"] = weights
    g.es["edge_type"] = edge_types
    g.es["contract_count"] = contract_counts

    # 5. Community detection
    partition = leidenalg.find_partition(
        g, leidenalg.ModularityVertexPartition,
        weights=g.es["weight"] if g.ecount() > 0 else None
    )
    g.vs["community"] = partition.membership

    # 6. Save
    g.write_pickle(output_path)

    # 7. Save metadata
    meta = {
        "recipient_count": sum(1 for v in g.vs if v["type"] == "recipient"),
        "psc_count": sum(1 for v in g.vs if v["type"] == "psc"),
        "naics_count": sum(1 for v in g.vs if v["type"] == "naics"),
        "edge_count": g.ecount(),
        "community_count": max(partition.membership) + 1 if partition.membership else 0,
    }
    meta_path = output_path.replace(".pkl", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build knowledge graph from DOE contracts")
    parser.add_argument("--db", default="doe_contracts.db")
    parser.add_argument("--output", default="graph.pkl")
    parser.add_argument("--topics-db", default=None)
    args = parser.parse_args()
    print(f"Building graph from {args.db}...")
    stats = build_graph(args.db, args.output, args.topics_db)
    print(f"Graph built: {stats}")
