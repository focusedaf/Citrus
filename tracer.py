import requests

BASE_URL = "https://api.etherscan.io/v2/api"

# Real, verified contract addresses for widely-impersonated tokens.
# If a transfer claims one of these symbols but comes from a DIFFERENT
# contract address, it's not the real token - it's a lookalike/scam token.
KNOWN_REAL_TOKEN_CONTRACTS = {
    "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "DAI": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "WETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
}


def _is_spoofed_token(symbol, contract_address):
   
    symbol = symbol or ""
    if not symbol.isascii():
        return True

    upper = symbol.upper()
    if upper in KNOWN_REAL_TOKEN_CONTRACTS:
        real_address = KNOWN_REAL_TOKEN_CONTRACTS[upper]
        if (contract_address or "").lower() != real_address:
            return True

    return False


def _fetch(action, address, api_key, chain_id, limit):
    url = (
        f"{BASE_URL}?chainid={chain_id}"
        f"&module=account&action={action}&address={address}"
        f"&sort=desc&apikey={api_key}"
    )
    resp = requests.get(url).json()
    if resp.get("status") != "1":
        print(f"[tracer] {action} -> {resp.get('message')}: {resp.get('result')}")
        return []
    return resp["result"][:limit]


def get_eth_transactions(address, api_key, chain_id=1, limit=10):
  
    raw = _fetch("txlist", address, api_key, chain_id, limit)
    outgoing = [tx for tx in raw if tx["from"].lower() == address.lower()]

    results = []
    for tx in outgoing:
        tx_type = "eth_transfer" if tx.get("input", "0x") == "0x" else "contract_interaction"
        results.append({
            "from": tx["from"], "to": tx["to"], "value": tx["value"],
            "token": "ETH", "type": tx_type, "tx_hash": tx["hash"],
            "timestamp": int(tx["timeStamp"]), "is_spoofed_token": False,
        })
    return results


def get_token_transactions(address, api_key, chain_id=1, limit=10):
  
    raw = _fetch("tokentx", address, api_key, chain_id, limit)
    outgoing = [tx for tx in raw if tx["from"].lower() == address.lower()]

    results = []
    for tx in outgoing:
        decimals = int(tx.get("tokenDecimal", 18) or 18)
        symbol = tx.get("tokenSymbol", "UNKNOWN")
        contract_address = tx.get("contractAddress", "")
        spoofed = _is_spoofed_token(symbol, contract_address)
        results.append({
            "from": tx["from"], "to": tx["to"],
            "value": tx["value"], "value_decimals": decimals,
            "token": symbol, "token_contract": contract_address,
            "type": "erc20_transfer", "tx_hash": tx["hash"],
            "timestamp": int(tx["timeStamp"]), "is_spoofed_token": spoofed,
        })
    return results


def get_internal_transactions(address, api_key, chain_id=1, limit=10):
  
    raw = _fetch("txlistinternal", address, api_key, chain_id, limit)
    outgoing = [tx for tx in raw if tx["from"].lower() == address.lower()]

    results = []
    for tx in outgoing:
        results.append({
            "from": tx["from"], "to": tx["to"], "value": tx["value"],
            "token": "ETH", "type": "internal_transfer",
            "tx_hash": tx.get("hash", ""), "timestamp": int(tx["timeStamp"]),
            "is_spoofed_token": False,
        })
    return results


# Transaction types whose `to` address represents a real wallet/entity
# worth continuing the trace from.
HOPPABLE_TYPES = {"eth_transfer", "erc20_transfer", "internal_transfer"}


def get_all_transactions(address, api_key, chain_id=1, limit_per_type=5):
   
    eth = get_eth_transactions(address, api_key, chain_id, limit_per_type)
    tokens = get_token_transactions(address, api_key, chain_id, limit_per_type)
    internal = get_internal_transactions(address, api_key, chain_id, limit_per_type)
    return eth + tokens + internal


def trace_wallet(start_address, api_key, chain_id=1, max_hops=3, limit_per_type=5):
    
    all_edges = []
    current_layer = [start_address]
    visited = set()

    for hop in range(max_hops):
        next_layer = []
        for addr in current_layer:
            if addr.lower() in visited:
                continue
            visited.add(addr.lower())

            txns = get_all_transactions(addr, api_key, chain_id, limit_per_type)
            for tx in txns:
                tx["hop"] = hop
                all_edges.append(tx)
                if tx["type"] in HOPPABLE_TYPES and tx["to"]:
                    next_layer.append(tx["to"])

        current_layer = next_layer
        if not current_layer:
            break

    return all_edges