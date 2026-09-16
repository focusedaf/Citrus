LARGE_VALUE_ETH_THRESHOLD = 5.0
DEEP_HOP_THRESHOLD = 3
FAN_OUT_THRESHOLD = 5

WEIGHTS = {
    "mixer_exposure": 40,
    "spoofed_token": 35,   # scam-token exposure is a strong phishing/scam signal
    "bridge_exposure": 25,
    "vasp_exposure": 30,
    "deep_hops": 15,
    "fan_out": 15,
    "large_value": 10,
}

RISK_THRESHOLDS = [
    (75, "Critical"),
    (50, "High"),
    (25, "Medium"),
    (0, "Low"),
]


def _to_eth(edge):
    if edge["token"] != "ETH":
        return 0.0
    return float(edge["value"]) / 1e18


def compute_metrics(edges, tags):
    unique_hops = max([e["hop"] for e in edges], default=-1) + 1
    transaction_count = len(edges)
    unique_counterparties = len({e["to"] for e in edges if e["to"]})

    matched_types = {tag["entity_type"] for tag in tags.values() if tag}
    vasp_exposure = "vasp" in matched_types
    bridge_exposure = "bridge" in matched_types
    mixer_exposure = "mixer" in matched_types

    # Fan-out: distinct addresses funded DIRECTLY from the source (hop 0).
    fan_out = len({e["to"] for e in edges if e["hop"] == 0 and e["to"]})

    large_value = any(_to_eth(e) >= LARGE_VALUE_ETH_THRESHOLD for e in edges)

    spoofed_edges = [e for e in edges if e.get("is_spoofed_token")]
    spoofed_token_detected = len(spoofed_edges) > 0

    return {
        "unique_hops": unique_hops,
        "transaction_count": transaction_count,
        "unique_counterparties": unique_counterparties,
        "vasp_exposure": vasp_exposure,
        "bridge_exposure": bridge_exposure,
        "mixer_exposure": mixer_exposure,
        "fan_out": fan_out,
        "large_value_transfer": large_value,
        "spoofed_token_detected": spoofed_token_detected,
        "spoofed_token_count": len(spoofed_edges),
    }


def compute_risk(edges, tags, start_address=None):
    if not edges:
        return {
            "score": 0, "level": "Low",
            "label": "Rule-Based Risk Indicator (Prototype)",
            "reasons": [], "metrics": {},
        }

    metrics = compute_metrics(edges, tags)
    score = 0
    reasons = []

    if metrics["mixer_exposure"]:
        score += WEIGHTS["mixer_exposure"]
        reasons.append(f"+{WEIGHTS['mixer_exposure']} funds passed through a known mixer")

    if metrics["spoofed_token_detected"]:
        score += WEIGHTS["spoofed_token"]
        reasons.append(
            f"+{WEIGHTS['spoofed_token']} spoofed/lookalike token detected "
            f"({metrics['spoofed_token_count']} transfer(s) impersonating a known token)"
        )

    if metrics["bridge_exposure"]:
        score += WEIGHTS["bridge_exposure"]
        reasons.append(f"+{WEIGHTS['bridge_exposure']} funds crossed a known bridge (cross-chain movement)")

    if metrics["vasp_exposure"]:
        score += WEIGHTS["vasp_exposure"]
        reasons.append(f"+{WEIGHTS['vasp_exposure']} funds reached a known VASP")

    if metrics["unique_hops"] >= DEEP_HOP_THRESHOLD:
        score += WEIGHTS["deep_hops"]
        reasons.append(f"+{WEIGHTS['deep_hops']} deep layering ({metrics['unique_hops']} hops)")

    if metrics["fan_out"] >= FAN_OUT_THRESHOLD:
        score += WEIGHTS["fan_out"]
        reasons.append(f"+{WEIGHTS['fan_out']} fan-out pattern ({metrics['fan_out']} addresses funded directly from source)")

    if metrics["large_value_transfer"]:
        score += WEIGHTS["large_value"]
        reasons.append(f"+{WEIGHTS['large_value']} large single transfer (>= {LARGE_VALUE_ETH_THRESHOLD} ETH)")

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