"""
rule-based risk scoring (v1) later will replace/augment with a GNN-based model trained on
elliptic-style labeled transaction data

"""

HOP_PENALTY = 5          # points per hop in the traced path
EXCHANGE_BONUS = 30      # funds reached a known, identifiable exchange
BRIDGE_BONUS = 25        # funds crossed a known bridge contract (harder to trace)

RISK_THRESHOLDS = [
    (75, "Critical"),
    (50, "High"),
    (25, "Medium"),
    (0, "Low"),
]


def compute_risk(edges, tags):
   
    score = 0
    reasons = []

    hop_count = len(edges)
    hop_points = hop_count * HOP_PENALTY
    if hop_points:
        score += hop_points
        reasons.append(f"+{hop_points} for {hop_count} traced hop(s)")

    matched_types = {tag["type"] for tag in tags.values() if tag}

    if "exchange" in matched_types:
        score += EXCHANGE_BONUS
        reasons.append(f"+{EXCHANGE_BONUS} funds reached a known exchange")

    if "bridge" in matched_types:
        score += BRIDGE_BONUS
        reasons.append(f"+{BRIDGE_BONUS} funds crossed a known bridge (cross-chain movement)")

    score = min(score, 100)

    level = "Low"
    for threshold, label in RISK_THRESHOLDS:
        if score >= threshold:
            level = label
            break

    return {"score": score, "level": level, "reasons": reasons}