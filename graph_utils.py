import networkx as nx
from pyvis.network import Network
from collections import defaultdict

ENTITY_COLORS = {
    "vasp": "#e74c3c",
    "bridge": "#f39c12",
    "mixer": "#8e44ad",
    "contract": "#7f8c8d",
}

UNIDENTIFIED_COLOR = "#3498db"
REPORTED_COLOR = "#f1c40f"      # gold - the wallet under investigation
SPOOFED_EDGE_COLOR = "#e74c3c"  # red - a transfer involving a fake/lookalike token
NORMAL_EDGE_COLOR = "#5dade2"


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
            is_spoofed_token=e.get("is_spoofed_token", False),
        )
    return G


def _short_addr(addr, front=10, back=6):
   
    if len(addr) <= front + back + 3:
        return addr
    return f"{addr[:front]}...{addr[-back:]}"


def _format_amount(value):
    if value == 0:
        return "0"
    if abs(value) >= 1_000_000 or abs(value) < 0.000001:
        return f"{value:.3e}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def aggregate_edges(G):
   
    agg = defaultdict(lambda: {
        "tx_count": 0,
        "totals": defaultdict(float),
        "spoofed": False,
        "hops": set(),
    })

    for src, dst, data in G.edges(data=True):
        entry = agg[(src, dst)]
        entry["tx_count"] += 1
        entry["hops"].add(data["hop"])

        token_key = data["token"]
        if data.get("is_spoofed_token"):
            token_key = f"{data['token']} [FAKE]"
            entry["spoofed"] = True

        entry["totals"][token_key] += data["amount"]

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
            "entity_type": tag["entity_type"] if tag else "unknown",
            "entity_subtype": tag["entity_subtype"] if tag else "unknown",
            "hop": min(hops) if hops else None,
            "transaction_count": G.in_degree(node) + G.out_degree(node),
        })
    return rows


def investigation_summary(G, tags, edges, start_address, risk, cross_chain_findings=None):
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
        "cross_chain_activity": list((cross_chain_findings or {}).keys()) or "None detected",
        "risk_indicators": risk["reasons"],
        "risk_level": risk["level"],
        "risk_score": risk["score"],
    }


def _node_style(node, tag, is_start, degree):
    short = _short_addr(node)

    if is_start:
        shape = "hexagon"
        color = {
            "background": REPORTED_COLOR,
            "border": "#ffffff",
            "highlight": {"background": REPORTED_COLOR, "border": "#ffffff"},
        }
        border_width = 3
        entity_line = "REPORTED WALLET - trace start"
    elif tag:
        shape = "dot"
        base = ENTITY_COLORS.get(tag["entity_type"], UNIDENTIFIED_COLOR)
        color = {
            "background": base,
            "border": base,
            "highlight": {"background": base, "border": "#ffffff"},
        }
        border_width = 1
        entity_line = f"{tag['label']} ({tag['entity_type'].upper()})"
    else:
        shape = "dot"
        color = {
            "background": UNIDENTIFIED_COLOR,
            "border": UNIDENTIFIED_COLOR,
            "highlight": {"background": UNIDENTIFIED_COLOR, "border": "#ffffff"},
        }
        border_width = 1
        entity_line = "Unidentified wallet"

    label = f"{short}\n{entity_line}" if (is_start or tag) else short

    # Size scales gently with how connected the node is, so hubs stand
    # out in the layout instead of every node looking equally important.
    size = 16 + min(degree, 12) * 2
    if is_start:
        size += 6

    title_lines = [
        f"Full address: {node}",
        entity_line,
        f"Connections: {degree}",
    ]
    title = "\n".join(title_lines)

    return label, color, shape, size, border_width, title


def _edge_style(data):
    tx_count = data["tx_count"]
    totals_str = ", ".join(
        f"{_format_amount(amt)} {tok}"
        for tok, amt in sorted(data["totals"].items())
    )
    hop_str = ", ".join(str(h) for h in sorted(data["hops"]))

    if data["spoofed"]:
        color = SPOOFED_EDGE_COLOR
        dashes = True
        edge_label = f"⚠ {tx_count}x"
    else:
        color = NORMAL_EDGE_COLOR
        dashes = False
        edge_label = f"{tx_count}x"

    title_lines = [
        f"{tx_count} transaction(s) at hop(s) {hop_str}",
        f"Total moved: {totals_str}",
    ]
    if data["spoofed"]:
        title_lines.append("⚠ Includes a spoofed/lookalike token transfer")

    title = "\n".join(title_lines)
    width = 1 + min(tx_count, 8)

    return edge_label, color, dashes, width, title


LEGEND_HTML = """
<div id="citrus-legend" style="
    position:fixed; top:14px; right:14px; z-index:1000;
    background:#1a1a1a; border:1px solid #3a3a3a; border-radius:10px;
    padding:14px 16px; color:#eee;
    font-family:Inter,system-ui,-apple-system,'Segoe UI',sans-serif;
    font-size:12px; line-height:1.9; width:220px;
    box-shadow:0 4px 18px rgba(0,0,0,0.5);
">
    <div style="font-weight:700; font-size:13px; margin-bottom:8px;">Legend</div>
    <div><span style="display:inline-block;width:13px;height:13px;background:#f1c40f;border:1px solid #ffffff;margin-right:8px;clip-path:polygon(25% 0%,75% 0%,100% 50%,75% 100%,25% 100%,0% 50%);"></span>Reported wallet (trace start)</div>
    <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#e74c3c;margin-right:8px;"></span>Known VASP / exchange</div>
    <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f39c12;margin-right:8px;"></span>Known bridge</div>
    <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#8e44ad;margin-right:8px;"></span>Known mixer / tumbler</div>
    <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#7f8c8d;margin-right:8px;"></span>Known infrastructure contract</div>
    <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#3498db;margin-right:8px;"></span>Unidentified wallet</div>
    <hr style="border:none;border-top:1px solid #3a3a3a;margin:8px 0;">
    <div><span style="display:inline-block;width:18px;height:2px;background:#5dade2;margin-right:8px;vertical-align:middle;"></span>Normal transfer(s)</div>
    <div><span style="display:inline-block;width:18px;height:2px;background:#e74c3c;margin-right:8px;vertical-align:middle;border-top:2px dashed #e74c3c;"></span>⚠ Spoofed/fake token transfer</div>
    <hr style="border:none;border-top:1px solid #3a3a3a;margin:8px 0;">
    <div style="color:#888;">Edge label = transaction count. Hover any node or edge for full details.</div>
</div>
"""


def _inject_legend(output_file):
    """
    pyvis has no built-in legend, so append a small fixed-position
    overlay describing the color/line coding directly into the
    generated HTML file.
    """
    with open(output_file, "r", encoding="utf-8") as f:
        html = f.read()

    if "</body>" in html:
        html = html.replace("</body>", LEGEND_HTML + "</body>")
    else:
        html += LEGEND_HTML

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)


def render_graph(G, tags=None, start_address=None, output_file="graph.html"):
    net = Network(
        directed=True,
        height="820px",
        width="100%",
        bgcolor="#1e1e1e",
        font_color="white",
        cdn_resources="remote",
    )

    tags = tags or {}
    start_lower = start_address.lower() if start_address else None

    for node in G.nodes:
        tag = tags.get(node)
        is_start = bool(start_lower) and node.lower() == start_lower
        degree = G.in_degree(node) + G.out_degree(node)

        label, color, shape, size, border_width, title = _node_style(node, tag, is_start, degree)

        net.add_node(
            node,
            label=label,
            color=color,
            shape=shape,
            size=size,
            borderWidth=border_width,
            shadow=True,
            title=title,
            font={"size": 13, "color": "#f5f5f5", "multi": False},
        )

    for (src, dst), data in aggregate_edges(G).items():
        edge_label, color, dashes, width, title = _edge_style(data)

        net.add_edge(
            src, dst,
            label=edge_label,
            title=title,
            color=color,
            width=width,
            dashes=dashes,
            arrows="to",
            font={"size": 11, "color": "#ccc", "strokeWidth": 0},
        )

    # Hierarchical, left-to-right layout: since this graph represents a
    # directed BFS trace of fund movement (source -> later hops), laying
    # it out by edge direction reads naturally left-to-right like a
    # money-flow diagram, instead of the previous force-directed "hairball"
    # where hop order and flow direction were impossible to follow visually.
    net.set_options("""
    {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "LR",
          "sortMethod": "directed",
          "levelSeparation": 320,
          "nodeSpacing": 220,
          "treeSpacing": 260,
          "blockShifting": true,
          "edgeMinimization": true,
          "parentCentralization": true
        }
      },
      "physics": {
        "enabled": true,
        "hierarchicalRepulsion": {
          "nodeDistance": 220,
          "springLength": 220,
          "avoidOverlap": 0.6
        },
        "solver": "hierarchicalRepulsion"
      },
      "edges": {
        "smooth": {
          "type": "cubicBezier",
          "forceDirection": "horizontal",
          "roundness": 0.5
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 120,
        "navigationButtons": true,
        "keyboard": true
      }
    }
    """)

    net.show(output_file, notebook=False)
    _inject_legend(output_file)

    return output_file