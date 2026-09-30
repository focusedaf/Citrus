import json
import math
from collections import Counter
from datetime import datetime, timezone

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
    <span class="legend-dot hot"></span>
    <span>Hot-wallet-like</span>
  </div>

  <div class="legend-item">
    <span class="legend-dot cold"></span>
    <span>Cold-wallet-like</span>
  </div>

  <div class="legend-item">
    <span class="legend-dot intermediary"></span>
    <span>Intermediary wallet</span>
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
    <span class="legend-dot mixer"></span>
    <span>Mixer</span>
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

    If `amount` exists without `value`, it is assumed to already be
    human-readable.
    """
    value = _safe_float(
        edge_data.get("value")
        if edge_data.get("value") is not None
        else edge_data.get("amount")
    )

    if (
        edge_data.get("amount") is not None
        and edge_data.get("value") is None
    ):
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
        or edge_data.get("asset")
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


def _tag_name(tag):
    if isinstance(tag, dict):
        return (
            tag.get("name")
            or tag.get("label")
            or tag.get("tag")
        )

    if tag:
        return str(tag)

    return None


def _entity_type(node, node_data, tags=None, start_address=None):
    """
    Determine the broad entity class.

    Priority:
      1. Explicit reported address
      2. Tagging result
      3. Node metadata
      4. Unknown

    Wallet behavioral classification is handled separately by
    `_wallet_behavior`.
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

            if entity_type in {"contract", "token"}:
                return "contract"

            if entity_type in {"wallet", "address", "user"}:
                return "wallet"

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

    return labels.get(
        entity_type,
        entity_type.replace("_", " ").title(),
    )


def _wallet_behavior_label(behavior):
    labels = {
        "suspect_wallet": "Suspect wallet",
        "hot_wallet": "Hot-wallet-like",
        "cold_wallet": "Cold-wallet-like",
        "intermediary": "Intermediary wallet",
        "wallet": "Wallet",
        "unknown": "Wallet - insufficient evidence",
    }

    return labels.get(
        behavior,
        str(behavior).replace("_", " ").title(),
    )


def _node_color(node_data, is_start=False, entity_type=None, behavior=None):
    if is_start:
        return "#ef4444"

    if behavior == "hot_wallet":
        return "#f97316"

    if behavior == "cold_wallet":
        return "#0ea5e9"

    if behavior == "intermediary":
        return "#eab308"

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


def _node_shape(node_data, is_start=False, entity_type=None, behavior=None):
    if is_start:
        return "star"

    if behavior == "intermediary":
        return "diamond"

    if behavior == "cold_wallet":
        return "square"

    if behavior == "hot_wallet":
        return "dot"

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


def _edge_type(edge_data):
    return str(
        edge_data.get("type")
        or edge_data.get("tx_type")
        or edge_data.get("category")
        or "transfer"
    ).lower()


def _is_contract_interaction(edge_data):
    edge_type = _edge_type(edge_data)

    return edge_type in {
        "contract_interaction",
        "contract_call",
        "contract",
        "interaction",
        "call",
    }


def _is_value_transfer(edge_data):
    """
    Decide whether an edge represents a meaningful value movement.

    We intentionally keep contract interactions in the graph, but they
    are rendered as secondary/dashed edges rather than being mistaken
    for fund-flow hops.
    """
    if _is_contract_interaction(edge_data):
        return False

    amount = _normalized_amount(edge_data)

    edge_type = _edge_type(edge_data)

    if amount > 0:
        return True

    return edge_type in {
        "eth_transfer",
        "erc20_transfer",
        "internal",
        "internal_transfer",
        "token_transfer",
        "transfer",
        "native_transfer",
    }


def _timestamp_value(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        number = float(value)

        if number > 10_000_000_000:
            return number / 1000.0

        return number

    text = str(value).strip()

    if not text:
        return None

    try:
        number = float(text)

        if number > 10_000_000_000:
            return number / 1000.0

        return number

    except ValueError:
        pass

    try:
        normalized = text.replace("Z", "+00:00")

        dt = datetime.fromisoformat(normalized)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.timestamp()

    except (TypeError, ValueError, OverflowError):
        return None


def _wallet_behavior(node, G, entity_type):
    """
    Infer wallet behaviour from observable transaction activity.

    This is intentionally conservative.

    We do NOT claim to know physical key storage. The labels mean:
      - hot_wallet: highly active wallet behaviour
      - cold_wallet: storage-like / low outgoing activity
      - intermediary: receives and forwards funds
      - wallet: insufficient evidence for a stronger classification
    """
    if entity_type not in {"wallet", "reported_wallet"}:
        return None, []

    incoming_edges = list(G.in_edges(node, data=True))
    outgoing_edges = list(G.out_edges(node, data=True))

    incoming_value_edges = [
        item for item in incoming_edges
        if _is_value_transfer(item[2])
    ]

    outgoing_value_edges = [
        item for item in outgoing_edges
        if _is_value_transfer(item[2])
    ]

    incoming_count = sum(
        int(_safe_float(data.get("count"), 1))
        for _, _, data in incoming_value_edges
    )

    outgoing_count = sum(
        int(_safe_float(data.get("count"), 1))
        for _, _, data in outgoing_value_edges
    )

    total_count = incoming_count + outgoing_count

    unique_counterparties = set()

    for source, _, _ in incoming_value_edges:
        unique_counterparties.add(source)

    for _, target, _ in outgoing_value_edges:
        unique_counterparties.add(target)

    incoming_assets = set()
    outgoing_assets = set()

    for _, _, data in incoming_value_edges:
        incoming_assets.add(_asset_symbol(data))

    for _, _, data in outgoing_value_edges:
        outgoing_assets.add(_asset_symbol(data))

    reasons = []

    # Suspect address is dealt with separately.
    if total_count == 0:
        return "unknown", [
            "No value-transfer activity available for behavioral classification."
        ]

    # Intermediary behaviour:
    # receives funds AND forwards funds.
    if incoming_count > 0 and outgoing_count > 0:
        forwarding_ratio = min(
            incoming_count,
            outgoing_count,
        ) / max(
            incoming_count,
            outgoing_count,
        )

        if (
            forwarding_ratio >= 0.25
            and len(unique_counterparties) >= 2
        ):
            reasons.append(
                "Receives and subsequently forwards value."
            )

            if outgoing_count >= 3:
                reasons.append(
                    f"{outgoing_count} outgoing value-transfer events observed."
                )

            return "intermediary", reasons

    # Activity-based hot-wallet inference.
    if outgoing_count >= 5 or total_count >= 10:
        reasons.append(
            f"High observed transaction activity ({total_count} value-transfer events)."
        )

        if outgoing_count >= 3:
            reasons.append(
                f"Frequent outgoing activity ({outgoing_count} outgoing events)."
            )

        if len(unique_counterparties) >= 4:
            reasons.append(
                f"Activity spans {len(unique_counterparties)} counterparties."
            )

        return "hot_wallet", reasons

    # Storage-like / cold-wallet inference.
    #
    # We require incoming activity but little/no outgoing activity.
    # This prevents an arbitrary low-activity wallet from being called cold.
    if incoming_count >= 1 and outgoing_count == 0:
        reasons.append(
            "Observed incoming value with no outgoing value-transfer activity in the traced data."
        )
        reasons.append(
            "Behaviour is storage-like based on the available trace."
        )

        return "cold_wallet", reasons

    if incoming_count >= 2 and outgoing_count <= 1:
        reasons.append(
            "Predominantly incoming value-transfer activity."
        )
        reasons.append(
            "Limited outgoing activity in the traced data."
        )

        return "cold_wallet", reasons

    return "wallet", [
        "Wallet activity detected, but available evidence is insufficient "
        "for a stronger behavioral classification."
    ]


def classify_wallets(
    G,
    tags=None,
    start_address=None,
):
    """
    Return behavioral classifications for wallet-like nodes.

    This is useful to both the graph and the PDF so both outputs use
    the same classification source.
    """
    results = {}

    start_address = (
        str(start_address).lower()
        if start_address
        else None
    )

    for node, data in G.nodes(data=True):
        entity_type = _entity_type(
            node,
            data,
            tags=tags,
            start_address=start_address,
        )

        if entity_type not in {"wallet", "reported_wallet"}:
            continue

        if start_address and node == start_address:
            behavior = "suspect_wallet"
            reasons = [
                "Address was supplied as the reported suspect wallet."
            ]
        else:
            behavior, reasons = _wallet_behavior(
                node,
                G,
                entity_type,
            )

        incoming_count = 0
        outgoing_count = 0

        for _, _, edge_data in G.in_edges(node, data=True):
            if _is_value_transfer(edge_data):
                incoming_count += int(
                    _safe_float(edge_data.get("count"), 1)
                )

        for _, _, edge_data in G.out_edges(node, data=True):
            if _is_value_transfer(edge_data):
                outgoing_count += int(
                    _safe_float(edge_data.get("count"), 1)
                )

        results[node] = {
            "address": node,
            "behavior": behavior,
            "label": _wallet_behavior_label(behavior),
            "confidence": (
                1.0
                if behavior == "suspect_wallet"
                else 0.8
                if behavior in {"intermediary", "hot_wallet", "cold_wallet"}
                else 0.4
            ),
            "incoming_transactions": incoming_count,
            "outgoing_transactions": outgoing_count,
            "reasons": reasons,
        }

    return results


def _aggregate_asset_totals(G):
    asset_totals = {}

    for _, _, data in G.edges(data=True):
        # Contract interactions generally do not represent transferred value.
        if not _is_value_transfer(data):
            continue

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
    value_edge_count = 0
    interaction_edge_count = 0

    asset_totals = _aggregate_asset_totals(G)

    for node, data in G.nodes(data=True):
        node_types[_node_type(data)] += 1

    for _, _, data in G.edges(data=True):
        edge_count += 1

        count = int(
            _safe_float(data.get("count"), 1)
        )

        transaction_count += count

        if _is_value_transfer(data):
            value_edge_count += 1
        else:
            interaction_edge_count += 1

    return {
        "nodes": G.number_of_nodes(),
        "edges": edge_count,
        "value_edges": value_edge_count,
        "interaction_edges": interaction_edge_count,
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
    min-width: 210px;
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

.legend-dot.hot {{
    background: #f97316;
}}

.legend-dot.cold {{
    background: #0ea5e9;
}}

.legend-dot.intermediary {{
    background: #eab308;
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

.legend-dot.mixer {{
    background: #dc2626;
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

.citrus-note {{
    margin-top: 8px;
    opacity: .75;
    font-size: 10px;
}}
</style>

<div id="citrus-stats">
    <strong>CITRUS Graph</strong><br>
    Nodes: {stats["nodes"]}<br>
    Connections: {stats["edges"]}<br>
    Value flows: {stats["value_edges"]}<br>
    Contract interactions: {stats["interaction_edges"]}<br>
    Transactions: {stats["transaction_count"]}<br>
    <br>
    <strong>Transferred assets</strong><br>
    {asset_lines}
    <div class="citrus-note">
        Contract interactions are shown as secondary links.
    </div>
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


def _merge_edge_data(existing, edge_data):
    current_amount = _normalized_amount(edge_data)

    existing["aggregated_amount"] = (
        _safe_float(existing.get("aggregated_amount"))
        + current_amount
    )

    existing["count"] = (
        int(_safe_float(existing.get("count"), 1)) + 1
    )

    current_type = _edge_type(edge_data)

    existing_types = existing.get("types", [])

    if not isinstance(existing_types, list):
        existing_types = [str(existing_types)]

    if current_type not in existing_types:
        existing_types.append(current_type)

    existing["types"] = existing_types

    asset = _asset_symbol(edge_data)

    existing_assets = existing.get("assets", [])

    if not isinstance(existing_assets, list):
        existing_assets = [str(existing_assets)]

    if asset not in existing_assets:
        existing_assets.append(asset)

    existing["assets"] = existing_assets

    tx_hash = (
        edge_data.get("tx_hash")
        or edge_data.get("hash")
    )

    existing_hashes = existing.get("tx_hashes", [])

    if not isinstance(existing_hashes, list):
        existing_hashes = [existing_hashes]

    if tx_hash and tx_hash not in existing_hashes:
        existing_hashes.append(tx_hash)

    existing["tx_hashes"] = existing_hashes

    if not existing.get("tx_hash") and tx_hash:
        existing["tx_hash"] = tx_hash

    if existing.get("token_symbol") is None:
        existing["token_symbol"] = edge_data.get("token_symbol")

    if existing.get("symbol") is None:
        existing["symbol"] = edge_data.get("symbol")

    if existing.get("asset") is None:
        existing["asset"] = edge_data.get("asset")

    return existing


def build_graph(edges, start_address=None):
    """
    Build a graph while preserving both:
      - value-transfer edges
      - contract-interaction edges

    They are kept separate using `is_value_transfer` so rendering can
    visually prioritize actual fund flow.
    """
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

        edge_data["is_value_transfer"] = _is_value_transfer(
            edge_data
        )

        edge_data["is_contract_interaction"] = (
            not edge_data["is_value_transfer"]
        )

        if G.has_edge(source, target):
            _merge_edge_data(
                G[source][target],
                edge_data,
            )

        else:
            edge_data["count"] = 1

            edge_data["aggregated_amount"] = (
                _normalized_amount(edge_data)
            )

            edge_data["types"] = [
                _edge_type(edge_data)
            ]

            edge_data["assets"] = [
                _asset_symbol(edge_data)
            ]

            tx_hash = (
                edge_data.get("tx_hash")
                or edge_data.get("hash")
            )

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
              "gravitationalConstant": -9000,
              "centralGravity": 0.35,
              "springLength": 210,
              "springConstant": 0.035,
              "damping": 0.9
            },
            "minVelocity": 0.75
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

    wallet_behaviors = classify_wallets(
        G,
        tags=tags,
        start_address=start_address,
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

        wallet_info = wallet_behaviors.get(node)

        behavior = (
            wallet_info.get("behavior")
            if wallet_info
            else None
        )

        label = data.get("label") or _short_address(node)

        title_parts = [
            f"<b>{label}</b>",
            f"Address: {node}",
            f"Entity: {_entity_label(entity_type)}",
        ]

        if wallet_info:
            title_parts.append(
                f"Behavior: {_wallet_behavior_label(behavior)}"
            )

            if wallet_info.get("confidence") is not None:
                title_parts.append(
                    f"Classification confidence: "
                    f"{wallet_info['confidence']:.0%}"
                )

            for reason in wallet_info.get("reasons", []):
                title_parts.append(
                    f"Reason: {reason}"
                )

        tag = _tag_for_node(node, tags)

        tag_name = _tag_name(tag)

        if tag_name:
            title_parts.append(
                f"Tag: {tag_name}"
            )

            label = f"{label}\\n{tag_name}"

        if isinstance(tag, dict):
            confidence = tag.get("confidence")

            if confidence is not None:
                title_parts.append(
                    f"Tag confidence: {confidence}"
                )

        if wallet_info and behavior not in {
            None,
            "wallet",
            "unknown",
        }:
            label = (
                f"{label}\\n"
                f"{_wallet_behavior_label(behavior)}"
            )

        title = "<br>".join(title_parts)

        net.add_node(
            node,
            label=label,
            title=title,
            color=_node_color(
                data,
                is_start=is_start,
                entity_type=entity_type,
                behavior=behavior,
            ),
            shape=_node_shape(
                data,
                is_start=is_start,
                entity_type=entity_type,
                behavior=behavior,
            ),
            size=32 if is_start else (
                25 if behavior in {
                    "hot_wallet",
                    "cold_wallet",
                    "intermediary",
                }
                else 20
            ),
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

        asset_text = ", ".join(
            str(x)
            for x in assets
            if str(x) != "UNKNOWN"
        )

        count = int(
            _safe_float(data.get("count"), 1)
        )

        is_value = data.get(
            "is_value_transfer",
            _is_value_transfer(data),
        )

        edge_type = _edge_type(data)

        if amount and asset_text:
            label = f"{_short_number(amount)} {asset_text}"
        elif asset_text:
            label = asset_text
        elif edge_type:
            label = edge_type.replace(
                "_",
                " ",
            ).title()
        else:
            label = ""

        title_parts = [
            (
                "Fund transfer"
                if is_value
                else "Contract interaction"
            ),
        ]

        title_parts.append(
            f"Type: {edge_type.replace('_', ' ').title()}"
        )

        if amount:
            title_parts.append(
                f"Aggregated value: "
                f"{_short_number(amount)}"
                + (f" {asset_text}" if asset_text else "")
            )

        title_parts.append(
            f"Transactions: {count}"
        )

        if asset_text:
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

        width = (
            max(
                2.5,
                min(
                    10.0,
                    2.5 + math.log10(amount + 1) * 1.8,
                ),
            )
            if is_value
            else 1.0
        )

        edge_kwargs = {
            "label": label,
            "title": "<br>".join(title_parts),
            "width": width,
        }

        if not is_value:
            edge_kwargs.update(
                {
                    "dashes": True,
                    "color": "#cbd5e1",
                    "font": {
                        "size": 9,
                        "color": "#94a3b8",
                    },
                }
            )

        net.add_edge(
            source,
            target,
            **edge_kwargs,
        )

    stats = _compute_stats(G)

    html = net.generate_html(notebook=False)

    html = _inject_overlays(
        html,
        stats,
    )

    return html.encode("utf-8")


def investigation_table(
    G,
    tags=None,
    start_address=None,
):
    rows = []

    wallet_behaviors = classify_wallets(
        G,
        tags=tags,
        start_address=start_address,
    )

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

        wallet_info = wallet_behaviors.get(node)

        rows.append(
            {
                "address": node,
                "label": label,
                "type": entity_type,
                "behavior": (
                    wallet_info.get("behavior")
                    if wallet_info
                    else None
                ),
                "behavior_label": (
                    wallet_info.get("label")
                    if wallet_info
                    else None
                ),
                "behavior_confidence": (
                    wallet_info.get("confidence")
                    if wallet_info
                    else None
                ),
                "behavior_reasons": (
                    wallet_info.get("reasons", [])
                    if wallet_info
                    else []
                ),
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


def _build_flow_paths(G, start_address, max_paths=10):
    """
    Build a compact set of meaningful value-flow paths.

    Contract interactions are excluded from these paths because they
    are not necessarily money movement.
    """
    if not start_address:
        return []

    start_address = str(start_address).lower()

    if start_address not in G:
        return []

    flow_graph = nx.DiGraph()

    for source, target, data in G.edges(data=True):
        if _is_value_transfer(data):
            flow_graph.add_edge(
                source,
                target,
            )

    if start_address not in flow_graph:
        return []

    paths = []

    try:
        reachable = nx.single_source_shortest_path(
            flow_graph,
            start_address,
            cutoff=6,
        )
    except nx.NetworkXError:
        return []

    for target, path in reachable.items():
        if target == start_address:
            continue

        if len(path) < 2:
            continue

        paths.append(path)

    paths.sort(
        key=lambda path: (
            len(path),
            path[-1],
        )
    )

    return paths[:max_paths]


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
            "reported_address": address,
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
            "total_value": {},
            "wallet_classifications": [],
            "flow_paths": [],
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
        if not _is_value_transfer(data):
            continue

        asset = _asset_symbol(data)

        if asset and asset != "UNKNOWN":
            assets_observed.add(asset)

    wallet_classifications = classify_wallets(
        G,
        tags=tags,
        start_address=address,
    )

    wallet_classification_list = list(
        wallet_classifications.values()
    )

    behavior_counts = Counter(
        item["behavior"]
        for item in wallet_classification_list
    )

    flow_paths = _build_flow_paths(
        G,
        address,
    )

    flow_path_strings = []

    for path in flow_paths:
        flow_path_strings.append(
            " -> ".join(
                _short_address(node)
                for node in path
            )
        )

    return {
        "address": address,
        "reported_address": address,
        "chain_id": chain_id,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "value_edges": stats["value_edges"],
        "interaction_edges": stats["interaction_edges"],
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
        "wallet_classifications": wallet_classification_list,
        "wallet_behavior_counts": dict(behavior_counts),
        "flow_paths": flow_path_strings,
        "risk": risk or {},
        "cross_chain": cross_chain or {},
    }