BASE_URL = "https://api.etherscan.io/v2/api"

# chain_id -> display name. Add more from Etherscan's supported chain
# list as needed - the API call shape doesn't change.
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
RAPID_MOVEMENT_SECONDS = 3600  # funds forwarded within 1 hour of receipt

DB_PATH = "citrus.db"
ALERT_LOG_PATH = "alerts.log"
REPORTS_DIR = "reports"
GRAPH_OUTPUT_DIR = "graphs"

# Set to a real webhook URL (Slack incoming webhook, Discord, generic
# endpoint) to actually deliver alerts instead of just logging them.
ALERT_WEBHOOK_URL = None