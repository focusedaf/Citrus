import json
import math
from collections import Counter, defaultdict

import networkx as nx
from pyvis.network import Network


LEGEND_HTML = """
<div id="citrus-legend">
  <div class="legend-title">CITRUS Investigation Graph</div>

  <div class="legend-item">
    <span class="legend-dot start"></span>
    <span>Suspect wallet</span>
  </div>

  <div class="legend-item">
    <span class="legend-dot wallet"></span>
    <span>Wallet</span>
  </div>

  <div class="legend-item">
    <span class="legend-dot exchange"></span>
    <span>Known VASP / Exchange</span>
  </div>

  <div class="legend-item">
    <span class="legend-dot bridge"></span>
    <span>Known Bridge</span>
  </div>

  <div class="legend-item">
    <span class="legend-dot contract"></span>
    <span>Contract</span>
  </div>
</div>
"""


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _short_address(address):
    if not address:
        return "Unknown"

    address = str(address)

    if len(address) <= 14:
        return address

    return f"{address[:7]}...{address[-5:]}"


def _node_type(node_data):
    return str(
        node_data.get("type")
        or node_data.get("tag")
        or node_data.get("category")
        or "wallet"
    ).lower()


def _node_color(node_data, is_start=False):
    if is_start:
        return "#ef4444"

    node_type = _node_type(node_data)

    if "exchange" in node_type or "vasp" in node_type:
        return "#22c55e"

    if "bridge" in node_type:
        return "#a855f7"

    if "contract" in node_type:
        return "#f59e0b"

    if "token" in node_type:
        return "#06b6d4"

    return "#64748b"


def _node_shape(node_data, is_start=False):
    if is_start:
        return "star"

    node_type = _node_type(node_data)

    if "contract" in node_type or "token" in node_type:
        return "box"

    if "exchange" in node_type or "vasp" in node_type:
        return "database"

    if "bridge" in node_type:
        return "diamond"

    return "dot"


def _edge_label(edge_data):
    edge_type = (
        edge_data.get("type")
        or edge_data.get("tx_type")
        or edge_data.get("category")
        or ""
    )

    token_symbol = (
        edge_data.get("token_symbol")
        or edge_data.get("symbol")
        or ""
    )

    value = edge_data.get("value")

    if token_symbol:
        if value not in (None, "", 0, "0"):
            return f"{_short_number(value)} {token_symbol}"
        return str(token_symbol)

    if edge_type:
        return str(edge_type).replace("_", " ").title()

    return ""


def _short_number(value):
    number = _safe_float(value)

    if number == 0:
        return "0"

    if abs(number) >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"

    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"

    if abs(number) >= 1_000:
        return f"{number / 1_000:.2f}K"

    if number >= 1:
        return f"{number:.4f}".rstrip("0").rstrip(".")

    return f"{number:.8f}".rstrip("0").rstrip(".")


def _compute_stats(G, edges_agg=None):
    node_types = Counter()
    total_value = 0.0
    edge_count = 0

    for _, data in G.nodes(data=True):
        node_types[_node_type(data)] += 1

    for _, _, data in G.edges(data=True):
        edge_count += 1
        total_value += _safe_float(
            data.get("value")
            or data.get("amount")
            or data.get("value_numeric")
        )

    return {
        "nodes": G.number_of_nodes(),
        "edges": edge_count,
        "total_value": total_value,
        "node_types": dict(node_types),
    }


def _controls_and_style_html(stats):
    stats_json = json.dumps(stats, default=str)

    return f"""
<style>
#citrus-legend {{
    position: fixed;
    top: 15px;
    left: 15px;
    z-index: 9999;
    background: rgba(15, 23, 42, 0.95);
    color: #f8fafc;
    padding: 14px 16px;
    border-radius: 10px;
    font-family: Arial, sans-serif;
    font-size: 13px;
    box-shadow: 0 4px 20px rgba(0,0,0,.25);
    min-width: 190px;
}}

.legend-title {{
    font-weight: 700;
    margin-bottom: 10px;
    font-size: 14px;
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 6px 0;
}}

.legend-dot {{
    width: 11px;
    height: 11px;
    display: inline-block;
    border-radius: 50%;
}}

.legend-dot.start {{
    background: #ef4444;
}}

.legend-dot.wallet {{
    background: #64748b;
}}

.legend-dot.exchange {{
    background: #22c55e;
}}

.legend-dot.bridge {{
    background: #a855f7;
}}

.legend-dot.contract {{
    background: #f59e0b;
}}

#citrus-stats {{
    position: fixed;
    top: 15px;
    right: 15px;
    z-index: 9999;
    background: rgba(15, 23, 42, 0.95);
    color: #f8fafc;
    padding: 12px 15px;
    border-radius: 10px;
    font-family: Arial, sans-serif;
    font-size: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,.25);
}}

#citrus-stats strong {{
    font-size: 14px;
}}
</style>

<div id="citrus-stats">
    <strong>CITRUS Graph</strong><br>
    Nodes: {stats["nodes"]}<br>
    Connections: {stats["edges"]}<br>
    Total value: {_short_number(stats["total_value"])}
</div>

<script>
window.CITRUS_GRAPH_STATS = {stats_json};
</script>
"""


def _inject_overlays(html, stats):
    overlay = LEGEND_HTML + _controls_and_style_html(stats)

    if "</body>" in html:
        return html.replace("</body>", overlay + "</body>")

    return html + overlay


def build_graph(edges, start_address=None):
    G = nx.DiGraph()

    if not edges:
        return G

    for edge in edges:
        if not isinstance(edge, dict):
            continue

        source = (
            edge.get("from")
            or edge.get("source")
            or edge.get("from_address")
        )

        target = (
            edge.get("to")
            or edge.get("target")
            or edge.get("to_address")
        )

        if not source or not target:
            continue

        source = str(source).lower()
        target = str(target).lower()

        source_data = {
            "label": _short_address(source),
            "address": source,
            "type": edge.get("from_type", "wallet"),
        }

        target_data = {
            "label": _short_address(target),
            "address": target,
            "type": edge.get("to_type", "wallet"),
        }

        if source not in G:
            G.add_node(source, **source_data)

        if target not in G:
            G.add_node(target, **target_data)

        edge_data = dict(edge)

        if G.has_edge(source, target):
            existing = G[source][target]

            existing["value"] = (
                _safe_float(existing.get("value"))
                + _safe_float(
                    edge_data.get("value")
                    or edge_data.get("amount")
                )
            )

            existing["count"] = existing.get("count", 1) + 1

            existing_types = existing.get("types", [])

            current_type = (
                edge_data.get("type")
                or edge_data.get("tx_type")
                or "transfer"
            )

            if current_type not in existing_types:
                existing_types.append(current_type)

            existing["types"] = existing_types

            if not existing.get("tx_hash"):
                existing["tx_hash"] = edge_data.get("tx_hash")

        else:
            edge_data["value"] = _safe_float(
                edge_data.get("value")
                or edge_data.get("amount")
            )

            edge_data["count"] = 1
            edge_data["types"] = [
                edge_data.get("type")
                or edge_data.get("tx_type")
                or "transfer"
            ]

            G.add_edge(source, target, **edge_data)

    if start_address:
        start_address = str(start_address).lower()

        if start_address in G.nodes:
            G.nodes[start_address]["is_start"] = True
            G.nodes[start_address]["type"] = "start"

    return G


def render_graph(G, tags=None, start_address=None):
    net = Network(
        height="900px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#111827",
        notebook=False,
    )

    net.set_options(
        """
        {
          "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true
          },
          "physics": {
            "enabled": true,
            "stabilization": {
              "enabled": true,
              "iterations": 1000
            },
            "barnesHut": {
              "gravitationalConstant": -8000,
              "centralGravity": 0.25,
              "springLength": 180,
              "springConstant": 0.04,
              "damping": 0.9
            }
          },
          "nodes": {
            "font": {
              "size": 13,
              "face": "Arial"
            },
            "borderWidth": 2,
            "shadow": true
          },
          "edges": {
            "arrows": {
              "to": {
                "enabled": true,
                "scaleFactor": 0.7
              }
            },
            "smooth": {
              "enabled": true,
              "type": "dynamic"
            },
            "font": {
              "size": 10,
              "align": "middle"
            }
          }
        }
        """
    )

    start_address = (
        str(start_address).lower()
        if start_address
        else None
    )

    for node, data in G.nodes(data=True):
        is_start = (
            bool(data.get("is_start"))
            or node.lower() == start_address
        )

        label = data.get("label") or _short_address(node)

        node_type = _node_type(data)

        title = (
            f"<b>{label}</b><br>"
            f"Address: {node}<br>"
            f"Type: {node_type}"
        )

        tag = None

        if tags:
            if isinstance(tags, dict):
                tag = tags.get(node) or tags.get(node.lower())

        if tag:
            if isinstance(tag, dict):
                tag_name = (
                    tag.get("name")
                    or tag.get("label")
                    or tag.get("tag")
                )

                if tag_name:
                    title += f"<br>Tag: {tag_name}"

                tag_type = tag.get("type")

                if tag_type:
                    title += f"<br>Tag type: {tag_type}"

                if tag_name:
                    label = f"{label}\\n{tag_name}"

            else:
                label = f"{label}\\n{tag}"
                title += f"<br>Tag: {tag}"

        net.add_node(
            node,
            label=label,
            title=title,
            color=_node_color(data, is_start),
            shape=_node_shape(data, is_start),
            size=28 if is_start else 20,
        )

    for source, target, data in G.edges(data=True):
        value = _safe_float(
            data.get("value")
            or data.get("amount")
        )

        label = _edge_label(data)

        tx_hash = (
            data.get("tx_hash")
            or data.get("hash")
            or data.get("transaction_hash")
        )

        title_parts = []

        if data.get("type"):
            title_parts.append(
                f"Type: {str(data['type']).replace('_', ' ').title()}"
            )

        if value:
            title_parts.append(f"Value: {_short_number(value)}")

        if data.get("token_symbol"):
            title_parts.append(
                f"Token: {data['token_symbol']}"
            )

        if tx_hash:
            title_parts.append(
                f"Tx: {tx_hash}"
            )

        title = "<br>".join(title_parts)

        width = max(
            1.5,
            min(8.0, 1.5 + math.log10(value + 1) * 1.5)
        )

        net.add_edge(
            source,
            target,
            label=label,
            title=title,
            width=width,
        )

    stats = _compute_stats(G)

    html = net.generate_html(notebook=False)

    html = _inject_overlays(html, stats)

    return html.encode("utf-8")


def investigation_table(G):
    rows = []

    for node, data in G.nodes(data=True):
        rows.append(
            {
                "address": node,
                "label": data.get("label") or _short_address(node),
                "type": _node_type(data),
                "in_degree": G.in_degree(node),
                "out_degree": G.out_degree(node),
                "degree": G.degree(node),
            }
        )

    rows.sort(
        key=lambda row: (
            row["degree"],
            row["out_degree"],
            row["in_degree"],
        ),
        reverse=True,
    )

    return rows


def investigation_summary(G):
    if G.number_of_nodes() == 0:
        return {
            "nodes": 0,
            "edges": 0,
            "wallets": 0,
            "contracts": 0,
            "exchanges": 0,
            "bridges": 0,
            "total_value": 0.0,
        }

    stats = _compute_stats(G)

    wallets = 0
    contracts = 0
    exchanges = 0
    bridges = 0

    for _, data in G.nodes(data=True):
        node_type = _node_type(data)

        if "exchange" in node_type or "vasp" in node_type:
            exchanges += 1
        elif "bridge" in node_type:
            bridges += 1
        elif "contract" in node_type or "token" in node_type:
            contracts += 1
        else:
            wallets += 1

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "wallets": wallets,
        "contracts": contracts,
        "exchanges": exchanges,
        "bridges": bridges,
        "total_value": stats["total_value"],
    }