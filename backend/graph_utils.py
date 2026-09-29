import json
import math
from collections import Counter

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

  <div class="legend-item">
    <span class="legend-dot unknown"></span>
    <span>Unknown Entity</span>
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


def _normalized_amount(edge_data):
    """
    Convert blockchain base-unit values into human-readable amounts.

    Examples:
      26000000000000000000 with 18 decimals -> 26
      1000000 with 6 decimals -> 1
    """
    value = _safe_float(
        edge_data.get("value")
        if edge_data.get("value") is not None
        else edge_data.get("amount")
    )

    # Some normalized edges may already provide a human-readable amount.
    if edge_data.get("amount") is not None and edge_data.get("value") is None:
        return _safe_float(edge_data.get("amount"))

    decimals = edge_data.get("value_decimals", 18)

    try:
        decimals = int(decimals)
    except (TypeError, ValueError):
        decimals = 18

    if decimals < 0 or decimals > 36:
        decimals = 18

    return value / (10 ** decimals)


def _asset_symbol(edge_data):
    return (
        edge_data.get("token_symbol")
        or edge_data.get("symbol")
        or edge_data.get("token")
        or "UNKNOWN"
    )


def _node_type(node_data):
    return str(
        node_data.get("type")
        or node_data.get("tag")
        or node_data.get("category")
        or "unknown"
    ).lower()


def _tag_for_node(node, tags):
    if not isinstance(tags, dict):
        return None

    node = str(node).lower()

    return tags.get(node) or tags.get(node.lower())


def _entity_type(node, node_data, tags=None, start_address=None):
    """
    Resolve the entity classification from the strongest available source.

    Priority:
      1. Explicit reported start address
      2. Tagging result
      3. Node metadata
      4. Unknown

    This prevents contracts from accidentally being classified as wallets.
    """
    node = str(node).lower()

    if start_address and node == str(start_address).lower():
        return "reported_wallet"

    tag = _tag_for_node(node, tags)

    if isinstance(tag, dict):
        entity_type = (
            tag.get("entity_type")
            or tag.get("type")
            or tag.get("category")
        )

        if entity_type:
            entity_type = str(entity_type).lower()

            if entity_type in {"exchange", "vasp"}:
                return "exchange"

            if entity_type == "bridge":
                return "bridge"

            if entity_type == "mixer":
                return "mixer"

            if entity_type == "contract":
                return "contract"

            if entity_type == "token":
                return "contract"

            if entity_type == "wallet":
                return "wallet"

            return entity_type

    node_type = _node_type(node_data)

    if "exchange" in node_type or "vasp" in node_type:
        return "exchange"

    if "bridge" in node_type:
        return "bridge"

    if "mixer" in node_type:
        return "mixer"

    if "contract" in node_type or "token" in node_type:
        return "contract"

    if "wallet" in node_type:
        return "wallet"

    if "start" in node_type:
        return "reported_wallet"

    return "unknown"


def _entity_label(entity_type):
    labels = {
        "reported_wallet": "Suspect wallet",
        "wallet": "Wallet",
        "contract": "Contract",
        "exchange": "Known VASP / Exchange",
        "bridge": "Known Bridge",
        "mixer": "Mixer",
        "unknown": "Unknown Entity",
    }

    return labels.get(entity_type, entity_type.replace("_", " ").title())


def _node_color(node_data, is_start=False, entity_type=None):
    if is_start:
        return "#ef4444"

    entity_type = entity_type or _node_type(node_data)

    if entity_type == "exchange":
        return "#22c55e"

    if entity_type == "bridge":
        return "#a855f7"

    if entity_type == "contract":
        return "#f59e0b"

    if entity_type == "mixer":
        return "#dc2626"

    if entity_type == "wallet":
        return "#64748b"

    return "#94a3b8"


def _node_shape(node_data, is_start=False, entity_type=None):
    if is_start:
        return "star"

    entity_type = entity_type or _node_type(node_data)

    if entity_type == "contract":
        return "box"

    if entity_type == "exchange":
        return "database"

    if entity_type == "bridge":
        return "diamond"

    if entity_type == "mixer":
        return "triangle"

    return "dot"


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

    if abs(number) >= 1:
        return f"{number:.4f}".rstrip("0").rstrip(".")

    return f"{number:.8f}".rstrip("0").rstrip(".")


def _edge_label(edge_data):
    edge_type = (
        edge_data.get("type")
        or edge_data.get("tx_type")
        or edge_data.get("category")
        or ""
    )

    token_symbol = _asset_symbol(edge_data)

    amount = _normalized_amount(edge_data)

    if token_symbol != "UNKNOWN":
        if amount:
            return f"{_short_number(amount)} {token_symbol}"

        return str(token_symbol)

    if edge_type:
        return str(edge_type).replace("_", " ").title()

    return ""


def _aggregate_asset_totals(G):
    """
    Return totals grouped by asset.

    This avoids incorrectly adding ETH, USDT, NFSC, etc.
    into one meaningless numeric total.
    """
    asset_totals = {}

    for _, _, data in G.edges(data=True):
        asset = _asset_symbol(data)
        amount = _normalized_amount(data)

        asset_totals[asset] = (
            asset_totals.get(asset, 0.0) + amount
        )

    return {
        asset: round(amount, 12)
        for asset, amount in asset_totals.items()
    }


def _compute_stats(G):
    node_types = Counter()
    edge_count = 0
    transaction_count = 0
    asset_totals = _aggregate_asset_totals(G)

    for node, data in G.nodes(data=True):
        node_types[_node_type(data)] += 1

    for _, _, data in G.edges(data=True):
        edge_count += 1

        transaction_count += int(
            _safe_float(data.get("count"), 1)
        )

    return {
        "nodes": G.number_of_nodes(),
        "edges": edge_count,
        "transaction_count": transaction_count,
        "asset_totals": asset_totals,
        "node_types": dict(node_types),
    }


def _controls_and_style_html(stats):
    stats_json = json.dumps(stats, default=str)

    asset_lines = ""

    for asset, amount in stats.get("asset_totals", {}).items():
        asset_lines += (
            f"{_short_number(amount)} {asset}<br>"
        )

    if not asset_lines:
        asset_lines = "None detected<br>"

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
    min-width: 200px;
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

.legend-dot.unknown {{
    background: #94a3b8;
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
    Transactions: {stats["transaction_count"]}<br>
    <br>
    <strong>Asset totals</strong><br>
    {asset_lines}
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
            "type": edge.get("from_type", "unknown"),
        }

        target_data = {
            "label": _short_address(target),
            "address": target,
            "type": edge.get("to_type", "unknown"),
        }

        if source not in G:
            G.add_node(source, **source_data)

        if target not in G:
            G.add_node(target, **target_data)

        edge_data = dict(edge)

        if G.has_edge(source, target):
            existing = G[source][target]

            existing_amount = _normalized_amount(existing)
            current_amount = _normalized_amount(edge_data)

            # Preserve aggregation in human-readable units.
            existing["aggregated_amount"] = (
                _safe_float(existing.get("aggregated_amount"))
                + current_amount
            )

            existing["count"] = (
                int(_safe_float(existing.get("count"), 1)) + 1
            )

            existing_types = existing.get("types", [])

            if not isinstance(existing_types, list):
                existing_types = [str(existing_types)]

            current_type = (
                edge_data.get("type")
                or edge_data.get("tx_type")
                or "transfer"
            )

            if current_type not in existing_types:
                existing_types.append(current_type)

            existing["types"] = existing_types

            existing_assets = existing.get("assets", [])

            if not isinstance(existing_assets, list):
                existing_assets = [str(existing_assets)]

            asset = _asset_symbol(edge_data)

            if asset not in existing_assets:
                existing_assets.append(asset)

            existing["assets"] = existing_assets

            existing_hashes = existing.get("tx_hashes", [])

            if not isinstance(existing_hashes, list):
                existing_hashes = [existing_hashes]

            tx_hash = edge_data.get("tx_hash")

            if tx_hash and tx_hash not in existing_hashes:
                existing_hashes.append(tx_hash)

            existing["tx_hashes"] = existing_hashes

            if not existing.get("tx_hash"):
                existing["tx_hash"] = tx_hash

            # Keep the original value for evidence compatibility,
            # but use aggregated_amount for graph display/statistics.
            existing["value"] = existing.get("value", 0)

            if existing.get("token_symbol") is None:
                existing["token_symbol"] = edge_data.get(
                    "token_symbol"
                )

            if existing.get("symbol") is None:
                existing["symbol"] = edge_data.get("symbol")

        else:
            edge_data["count"] = 1
            edge_data["aggregated_amount"] = _normalized_amount(
                edge_data
            )

            edge_data["types"] = [
                edge_data.get("type")
                or edge_data.get("tx_type")
                or "transfer"
            ]

            edge_data["assets"] = [
                _asset_symbol(edge_data)
            ]

            tx_hash = edge_data.get("tx_hash")

            edge_data["tx_hashes"] = (
                [tx_hash] if tx_hash else []
            )

            G.add_edge(
                source,
                target,
                **edge_data,
            )

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

        entity_type = _entity_type(
            node,
            data,
            tags=tags,
            start_address=start_address,
        )

        label = data.get("label") or _short_address(node)

        title = (
            f"<b>{label}</b><br>"
            f"Address: {node}<br>"
            f"Entity: {_entity_label(entity_type)}"
        )

        tag = _tag_for_node(node, tags)

        if isinstance(tag, dict):
            tag_name = (
                tag.get("name")
                or tag.get("label")
                or tag.get("tag")
            )

            confidence = tag.get("confidence")

            if tag_name:
                title += f"<br>Tag: {tag_name}"
                label = f"{label}\\n{tag_name}"

            if confidence:
                title += f"<br>Confidence: {confidence}"

        elif tag:
            label = f"{label}\\n{tag}"
            title += f"<br>Tag: {tag}"

        net.add_node(
            node,
            label=label,
            title=title,
            color=_node_color(
                data,
                is_start=is_start,
                entity_type=entity_type,
            ),
            shape=_node_shape(
                data,
                is_start=is_start,
                entity_type=entity_type,
            ),
            size=28 if is_start else 20,
        )

    for source, target, data in G.edges(data=True):
        amount = _safe_float(
            data.get("aggregated_amount")
            if data.get("aggregated_amount") is not None
            else _normalized_amount(data)
        )

        assets = data.get("assets", [])

        if not isinstance(assets, list):
            assets = [str(assets)]

        if len(assets) == 1:
            asset_text = assets[0]
        else:
            asset_text = ", ".join(str(x) for x in assets)

        count = int(
            _safe_float(data.get("count"), 1)
        )

        label = ""

        if amount:
            label = f"{_short_number(amount)} {asset_text}"

        elif asset_text and asset_text != "UNKNOWN":
            label = asset_text

        elif data.get("type"):
            label = str(
                data["type"]
            ).replace("_", " ").title()

        title_parts = []

        if data.get("type"):
            title_parts.append(
                f"Type: {str(data['type']).replace('_', ' ').title()}"
            )

        if amount:
            title_parts.append(
                f"Aggregated value: {_short_number(amount)} {asset_text}"
            )

        title_parts.append(
            f"Transactions: {count}"
        )

        if assets:
            title_parts.append(
                f"Assets: {asset_text}"
            )

        tx_hashes = data.get("tx_hashes", [])

        if isinstance(tx_hashes, list) and tx_hashes:
            if len(tx_hashes) == 1:
                title_parts.append(
                    f"Tx: {tx_hashes[0]}"
                )
            else:
                title_parts.append(
                    f"Tx hashes: {len(tx_hashes)}"
                )

        title = "<br>".join(title_parts)

        width = max(
            1.5,
            min(
                8.0,
                1.5 + math.log10(amount + 1) * 1.5,
            ),
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


def investigation_table(
    G,
    tags=None,
    start_address=None,
):
    rows = []

    for node, data in G.nodes(data=True):
        entity_type = _entity_type(
            node,
            data,
            tags=tags,
            start_address=start_address,
        )

        tag = _tag_for_node(node, tags)

        label = (
            data.get("label")
            or _short_address(node)
        )

        confidence = None

        if isinstance(tag, dict):
            label = (
                tag.get("label")
                or tag.get("name")
                or label
            )

            confidence = tag.get("confidence")

        rows.append(
            {
                "address": node,
                "label": label,
                "type": entity_type,
                "in_degree": G.in_degree(node),
                "out_degree": G.out_degree(node),
                "degree": G.degree(node),
                "confidence": confidence,
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


def investigation_summary(
    G,
    address=None,
    chain_id=None,
    tags=None,
    risk=None,
    cross_chain=None,
):
    if G.number_of_nodes() == 0:
        return {
            "address": address,
            "chain_id": chain_id,
            "nodes": 0,
            "edges": 0,
            "transactions_analyzed": 0,
            "wallets": 0,
            "contracts": 0,
            "exchanges": 0,
            "bridges": 0,
            "mixers": 0,
            "unknown_entities": 0,
            "assets_observed": [],
            "asset_totals": {},
            "total_value": 0.0,
            "risk": risk or {},
            "cross_chain": cross_chain or {},
        }

    stats = _compute_stats(G)

    wallets = 0
    contracts = 0
    exchanges = 0
    bridges = 0
    mixers = 0
    unknown_entities = 0

    assets_observed = set()

    for node, data in G.nodes(data=True):
        entity_type = _entity_type(
            node,
            data,
            tags=tags,
            start_address=address,
        )

        if entity_type in {"wallet", "reported_wallet"}:
            wallets += 1

        elif entity_type == "contract":
            contracts += 1

        elif entity_type == "exchange":
            exchanges += 1

        elif entity_type == "bridge":
            bridges += 1

        elif entity_type == "mixer":
            mixers += 1

        else:
            unknown_entities += 1

    for _, _, data in G.edges(data=True):
        asset = _asset_symbol(data)

        if asset and asset != "UNKNOWN":
            assets_observed.add(asset)

    return {
        "address": address,
        "chain_id": chain_id,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "transactions_analyzed": stats["transaction_count"],
        "wallets": wallets,
        "contracts": contracts,
        "exchanges": exchanges,
        "bridges": bridges,
        "mixers": mixers,
        "unknown_entities": unknown_entities,
        "assets_observed": sorted(assets_observed),
        "asset_totals": stats["asset_totals"],
        "total_value": stats["asset_totals"],
        "risk": risk or {},
        "cross_chain": cross_chain or {},
    }