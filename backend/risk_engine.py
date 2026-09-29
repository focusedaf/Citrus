from config import (
    LARGE_VALUE_ETH_THRESHOLD,
    DEEP_HOP_THRESHOLD,
    FAN_OUT_THRESHOLD,
    FAN_IN_THRESHOLD,
    RAPID_MOVEMENT_SECONDS,
)


WEIGHTS = {
    "mixer_exposure": 40,
    "spoofed_token": 35,
    "bridge_exposure": 25,
    "vasp_exposure": 30,
    "deep_hops": 15,
    "fan_out": 15,
    "fan_in": 15,
    "rapid_movement": 20,
    "large_value": 10,
    "cross_chain_activity": 20,
}


RISK_THRESHOLDS = [
    (75, "Critical"),
    (50, "High"),
    (25, "Medium"),
    (0, "Low"),
]


def _to_eth(edge):
    if edge.get("token") != "ETH":
        return 0.0

    try:
        return float(edge.get("value", 0)) / 1e18
    except (TypeError, ValueError):
        return 0.0


def compute_metrics(
    edges,
    tags,
    incoming_timestamps=None,
    cross_chain_findings=None,
):
    incoming_timestamps = incoming_timestamps or {}
    cross_chain_findings = cross_chain_findings or {}

    unique_hops = max(
        [e.get("hop", 0) for e in edges],
        default=-1,
    ) + 1

    transaction_count = len(edges)

    unique_counterparties = len(
        {
            e.get("to")
            for e in edges
            if e.get("to")
        }
    )

    matched_types = {
        tag.get("entity_type")
        for tag in tags.values()
        if tag
    }

    vasp_exposure = "vasp" in matched_types
    bridge_exposure = "bridge" in matched_types
    mixer_exposure = "mixer" in matched_types

    fan_out = len(
        {
            e.get("to")
            for e in edges
            if e.get("hop") == 0 and e.get("to")
        }
    )

    in_counts = {}

    for edge in edges:
        destination = edge.get("to")

        if destination:
            in_counts[destination] = (
                in_counts.get(destination, 0) + 1
            )

    fan_in = max(
        in_counts.values(),
        default=0,
    )

    large_value = any(
        _to_eth(edge) >= LARGE_VALUE_ETH_THRESHOLD
        for edge in edges
    )

    spoofed_edges = [
        edge
        for edge in edges
        if edge.get("is_spoofed_token")
    ]

    spoofed_token_detected = len(spoofed_edges) > 0

    rapid_movement_nodes = []

    for edge in edges:
        node = edge.get("from")

        if node not in incoming_timestamps:
            continue

        try:
            delta = (
                edge.get("timestamp", 0)
                - incoming_timestamps[node]
            )
        except (TypeError, ValueError):
            continue

        if 0 <= delta <= RAPID_MOVEMENT_SECONDS:
            rapid_movement_nodes.append(node)

    rapid_movement_detected = bool(
        rapid_movement_nodes
    )

    cross_chain_activity = bool(
        cross_chain_findings
    )

    return {
        "unique_hops": unique_hops,
        "transaction_count": transaction_count,
        "unique_counterparties": unique_counterparties,
        "vasp_exposure": vasp_exposure,
        "bridge_exposure": bridge_exposure,
        "mixer_exposure": mixer_exposure,
        "fan_out": fan_out,
        "fan_in": fan_in,
        "large_value_transfer": large_value,
        "spoofed_token_detected": spoofed_token_detected,
        "spoofed_token_count": len(spoofed_edges),
        "rapid_movement_detected": rapid_movement_detected,
        "rapid_movement_node_count": len(
            set(rapid_movement_nodes)
        ),
        "cross_chain_activity": cross_chain_activity,
        "cross_chain_chains_found": list(
            cross_chain_findings.keys()
        ),
    }

def compute_risk(
    edges,
    tags,
    start_address=None,
    incoming_timestamps=None,
    cross_chain_findings=None,
    address=None,
    cross_chain_results=None,
    max_hops=None,
):
    if start_address is None:
        start_address = address

    if cross_chain_findings is None:
        cross_chain_findings = (
            cross_chain_results
            if cross_chain_results is not None
            else {}
        )

    if not edges:
        return {
            "score": 0,
            "level": "Low",
            "label": "Rule-Based Risk Indicator (Prototype)",
            "reasons": [],
            "metrics": {},
        }

    metrics = compute_metrics(
        edges,
        tags,
        incoming_timestamps=incoming_timestamps,
        cross_chain_findings=cross_chain_findings,
    )

    score = 0
    reasons = []

    def add(key, text):
        nonlocal score

        score += WEIGHTS[key]
        reasons.append(
            f"+{WEIGHTS[key]} {text}"
        )

    if metrics["mixer_exposure"]:
        add(
            "mixer_exposure",
            "funds passed through a known mixer/tumbler",
        )

    if metrics["spoofed_token_detected"]:
        add(
            "spoofed_token",
            "spoofed/lookalike token detected "
            f"({metrics['spoofed_token_count']} transfer(s))",
        )

    if metrics["bridge_exposure"]:
        add(
            "bridge_exposure",
            "funds reached a known bridge",
        )

    if metrics["vasp_exposure"]:
        add(
            "vasp_exposure",
            "funds reached a known VASP",
        )

    if metrics["cross_chain_activity"]:
        chains = ", ".join(
            metrics["cross_chain_chains_found"]
        )

        add(
            "cross_chain_activity",
            "traced address also active on other "
            f"chains ({chains})",
        )

    if metrics["rapid_movement_detected"]:
        add(
            "rapid_movement",
            "rapid pass-through detected at "
            f"{metrics['rapid_movement_node_count']} "
            "node(s) "
            f"(funds forwarded within "
            f"{RAPID_MOVEMENT_SECONDS // 60} min of receipt)",
        )

    if metrics["unique_hops"] >= DEEP_HOP_THRESHOLD:
        add(
            "deep_hops",
            f"deep layering ({metrics['unique_hops']} hops)",
        )

    if metrics["fan_out"] >= FAN_OUT_THRESHOLD:
        add(
            "fan_out",
            "fan-out pattern "
            f"({metrics['fan_out']} addresses funded "
            "directly from source)",
        )

    if metrics["fan_in"] >= FAN_IN_THRESHOLD:
        add(
            "fan_in",
            "fan-in pattern "
            f"({metrics['fan_in']} sources converging "
            "on one address)",
        )

    if metrics["large_value_transfer"]:
        add(
            "large_value",
            "large single transfer "
            f"(>= {LARGE_VALUE_ETH_THRESHOLD} ETH)",
        )

    score = min(score, 100)

    level = "Low"

    for threshold, label in RISK_THRESHOLDS:
        if score >= threshold:
            level = label
            break

    return {
        "score": score,
        "level": level,
        "label": "Rule-Based Risk Indicator (Prototype)",
        "reasons": reasons,
        "metrics": metrics,
    }