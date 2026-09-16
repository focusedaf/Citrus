import networkx as nx
from pyvis.network import Network
from collections import defaultdict


def _display_value(edge):
    if edge["token"] == "ETH":
        return float(edge["value"]) / 1e18, "ETH"
    decimals = edge.get("value_decimals", 18)
    return float(edge["value"]) / (10 ** decimals), edge["token"]


def build_graph(edges):
   
    G = nx.MultiDiGraph()
    for e in edges:
        amount, token = _display_value(e)
        G.add_edge(
            e["from"], e["to"],
            key=e["tx_hash"] or f"{e['from']}-{e['to']}-{e['timestamp']}",
            amount=amount, token=token,
            tx_type=e["type"], hop=e["hop"],
            timestamp=e["timestamp"], tx_hash=e["tx_hash"],
        )
    return G


def aggregate_edges(G):
   
    agg = defaultdict(lambda: {"tx_count": 0, "totals": defaultdict(float)})
    for src, dst, data in G.edges(data=True):
        entry = agg[(src, dst)]
        entry["tx_count"] += 1
        entry["totals"][data["token"]] += data["amount"]
    return agg


def investigation_table(G, tags):
   
    rows = []
    for node in G.nodes:
        tag = tags.get(node)
        in_edges = list(G.in_edges(node, data=True))
        out_edges = list(G.out_edges(node, data=True))
        hops = [d["hop"] for _, _, d in in_edges] or [d["hop"] for _, _, d in out_edges]
        rows.append({
            "address": node,
            "entity": tag["label"] if tag else "Unidentified",
            "type": tag["type"] if tag else "unknown",
            "hop": min(hops) if hops else None,
            "transaction_count": G.in_degree(node) + G.out_degree(node),
        })
    return rows


def render_graph(G, tags=None, output_file="graph.html"):
   
    net = Network(directed=True, height="600px", width="100%", bgcolor="#1e1e1e", font_color="white")

    for node in G.nodes:
        tag = tags.get(node) if tags else None
        if tag:
            label = f"{node[:8]}...\n({tag['label']})"
            color = {"exchange": "#e74c3c", "bridge": "#f39c12", "mixer": "#8e44ad"}.get(tag["type"], "#3498db")
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