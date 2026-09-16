import requests

BASE_URL = "https://api.etherscan.io/v2/api"


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
            "timestamp": int(tx["timeStamp"]),
        })
    return results


def get_token_transactions(address, api_key, chain_id=1, limit=10):
    
    raw = _fetch("tokentx", address, api_key, chain_id, limit)
    outgoing = [tx for tx in raw if tx["from"].lower() == address.lower()]

    results = []
    for tx in outgoing:
        decimals = int(tx.get("tokenDecimal", 18) or 18)
        results.append({
            "from": tx["from"], "to": tx["to"],
            "value": tx["value"], "value_decimals": decimals,
            "token": tx.get("tokenSymbol", "UNKNOWN"),
            "type": "erc20_transfer", "tx_hash": tx["hash"],
            "timestamp": int(tx["timeStamp"]),
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
        })
    return results


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