import os

GRAPHS_DIR = os.getenv("GRAPHS_DIR", "graphs")
EVIDENCE_DIR = os.getenv("EVIDENCE_DIR", "evidence")
LABELS_FILE = os.getenv("LABELS_FILE", "labels.json")
ENABLE_CONTRACT_PROBING = os.getenv("ENABLE_CONTRACT_PROBING", "true").lower() == "true"

BASE_URL = "https://api.etherscan.io/v2/api"


SUPPORTED_CHAINS = {
    1: "Ethereum",
    56: "BNB Smart Chain",
    137: "Polygon",
    42161: "Arbitrum One",
    10: "Optimism",
    43114: "Avalanche C-Chain",
}

DEFAULT_CHAIN_ID = 1

# Risk engine thresholds
LARGE_VALUE_ETH_THRESHOLD = 5.0
DEEP_HOP_THRESHOLD = 3
FAN_OUT_THRESHOLD = 5
FAN_IN_THRESHOLD = 5
RAPID_MOVEMENT_SECONDS = 3600  

DB_PATH = "citrus.db"
ALERT_LOG_PATH = "alerts.log"
REPORTS_DIR = "reports"
GRAPH_OUTPUT_DIR = "graphs"


ALERT_WEBHOOK_URL = None

