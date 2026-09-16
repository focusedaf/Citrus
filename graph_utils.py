"""
graph_utils.py
Builds a transaction graph from traced edges and renders it as an
interactive HTML visualization using pyvis. Also produces an
investigator-oriented summary (investigation_summary) - the structured
"what did we find" readout, separate from the raw graph.

Uses a MultiDiGraph so multiple transactions between the same two
addresses are preserved individually, never collapsed.
"""

import networkx as nx
from pyvis.network import Network
from collections import defaultdict

ENTITY_COLORS = {
    "vasp": "#e74c3c",
    "bridge": "#f39c12",
    "mixer": "#8e44ad",
    "contract": "#7f8c8d",
}


def _display_value(edge):
    if edge["token"] == "ETH":
        return float(edge["value"]) / 1e18, "ETH"
    decimals = edge.get("value_decimals", 18)
    return float(edge["value"]) / (10 ** decimals), edge["token"]


def build_graph(edges):
    """
    edges: list of dicts from tracer.trace_wallet()
    Returns a NetworkX MultiDiGraph - one edge per real transaction.
    """
    G = nx.MultiDiGraph()
    for e in edges:
        amount, token = _display_value(e)
        G.add_edge(
            e["from"], e["to"],
            key=e["tx_hash"] or f"{e['from']}-{e['to']}-{e['timestamp']}",
            amount=amount, token=token,
            tx_type=e["type"], hop=e["hop"],
            timestamp=e["timestamp"], tx_hash=e["tx_hash"],
            is_spoofed_token=e.get("is_spoofed_token", False),
        )
    return G


def aggregate_edges(G):
    """
    Collapses parallel edges between the same (src, dst) pair for display:
    {(A, B): {"tx_count": 3, "totals": {"USDT": 7500.0, "ETH": 2.0}}}
    """
    agg = defaultdict(lambda: {"tx_count": 0, "totals": defaultdict(float)})
    for src, dst, data in G.edges(data=True):
        entry = agg[(src, dst)]
        entry["tx_count"] += 1
        entry["totals"][data["token"]] += data["amount"]
    return agg


def investigation_table(G, tags):
    """
    Investigator-readable rows: Address, Entity, Entity Type/Subtype,
    Hop, Transaction Count.
    """
    rows = []
    for node in G.nodes:
        tag = tags.get(node)
        in_edges = list(G.in_edges(node, data=True))
        out_edges = list(G.out_edges(node, data=True))
        hops = [d["hop"] for _, _, d in in_edges] or [d["hop"] for _, _, d in out_edges]
        rows.append({
            "address": node,
            "entity": tag["label"] if tag else "Unidentified",
            "entity_type": tag["entity_type"] if tag else "unknown",
            "entity_subtype": tag["entity_subtype"] if tag else "unknown",
            "hop": min(hops) if hops else None,
            "transaction_count": G.in_degree(node) + G.out_degree(node),
        })
    return rows


def investigation_summary(G, tags, edges, start_address, risk):
    """
    Produces the structured, investigator-facing readout: what was
    observed, which entities were identified, and why the risk score
    came out the way it did. This is the "report", separate from the
    raw graph data.
    """
    assets_observed = sorted({e["token"] for e in edges})
    max_hop = max([e["hop"] for e in edges], default=-1)

    vasps_found = sorted({t["label"] for t in tags.values() if t and t["entity_type"] == "vasp"})
    bridges_found = sorted({t["label"] for t in tags.values() if t and t["entity_type"] == "bridge"})
    mixers_found = sorted({t["label"] for t in tags.values() if t and t["entity_type"] == "mixer"})
    contracts_found = sorted({t["label"] for t in tags.values() if t and t["entity_type"] == "contract"})
    unidentified_count = sum(1 for t in tags.values() if t is None)

    spoofed = [e for e in edges if e.get("is_spoofed_token")]
    spoofed_tokens = sorted({e["token"] for e in spoofed})

    return {
        "reported_address": start_address,
        "chain": "Ethereum",
        "assets_observed": assets_observed,
        "transactions_analyzed": len(edges),
        "unique_counterparties": len(G.nodes) - 1 if len(G.nodes) > 0 else 0,
        "max_trace_depth": max_hop + 1 if max_hop >= 0 else 0,
        "entity_findings": {
            "vasp": vasps_found or "None detected",
            "bridge": bridges_found or "None detected",
            "mixer": mixers_found or "None detected",
            "known_contracts": contracts_found or "None detected",
            "unidentified_wallets": unidentified_count,
        },
        "spoofed_tokens_detected": spoofed_tokens or "None detected",
        "risk_indicators": risk["reasons"],
        "risk_level": risk["level"],
        "risk_score": risk["score"],
    }


def render_graph(G, tags=None, output_file="graph.html"):
    """
    Functional render (not styled yet). Nodes are colored by entity type
    (VASP / bridge / mixer / contract / unidentified wallet). Parallel
    edges between the same pair are aggregated into one visual line.
    """
    net = Network(directed=True, height="600px", width="100%", bgcolor="#1e1e1e", font_color="white")

    for node in G.nodes:
        tag = tags.get(node) if tags else None
        if tag:
            label = f"{node[:8]}...\n({tag['label']})"
            color = ENTITY_COLORS.get(tag["entity_type"], "#3498db")
        else:
            label = f"{node[:8]}..."
            color = "#3498db"
        net.add_node(node, label=label, color=color, title=node)

    for (src, dst), data in aggregate_edges(G).items():
        totals_str = ", ".join(f"{amt:.4f} {tok}" for tok, amt in data["totals"].items())
        label = f"{data['tx_count']} txn(s): {totals_str}"
        net.add_edge(src, dst, title=label, label=str(data["tx_count"]))

    net.show(output_file, notebook=False)
    return output_file