import time
import requests
from config import ALERT_LOG_PATH, ALERT_WEBHOOK_URL

ALERT_THRESHOLD_LEVELS = {"High", "Critical"}


def should_alert(risk):
    return risk.get("level") in ALERT_THRESHOLD_LEVELS


def _log_to_file(message):
    with open(ALERT_LOG_PATH, "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def _send_webhook(payload):
    if not ALERT_WEBHOOK_URL:
        return False
    try:
        requests.post(ALERT_WEBHOOK_URL, json=payload, timeout=5)
        return True
    except requests.RequestException as exc:
        print(f"[alert_engine] webhook delivery failed: {exc}")
        return False


def raise_alert(address, risk, trace_id=None):
   
    if not should_alert(risk):
        return None

    reasons = "; ".join(risk.get("reasons", []))
    message = (
        f"ALERT [{risk['level']}] wallet {address} scored {risk['score']}/100 "
        f"- {reasons}"
    )
    _log_to_file(message)
    _send_webhook({
        "address": address, "trace_id": trace_id,
        "risk_level": risk["level"], "risk_score": risk["score"],
        "reasons": risk.get("reasons", []),
    })
    print(f"[alert_engine] {message}")
    return message