"""
handles fetching transaction data from Etherscan and following outgoing transactions hop-by-hop (BFS) from a starting wallet address

"""

import requests

BASE_URL = "https://api.etherscan.io/v2/api"


def get_transactions(address, api_key, chain_id=1, limit=10):
    
    url = (
        f"{BASE_URL}"
        f"?chainid={chain_id}"
        f"&module=account&action=txlist&address={address}"
        f"&sort=desc&apikey={api_key}"
    )
    resp = requests.get(url).json()

    if resp.get("status") != "1":
        # status "0" can mean "no transactions found" OR an actual error
        print(f"[tracer] Etherscan returned: {resp.get('message')} - {resp.get('result')}")
        return []

    transactions = resp["result"]
    outgoing = [tx for tx in transactions if tx["from"].lower() == address.lower()]
    return outgoing[:limit]


def trace_wallet(start_address, api_key, chain_id=1, max_hops=3, txns_per_hop=5):
   
    graph_edges = []
    current_layer = [start_address]
    visited = set()

    for hop in range(max_hops):
        next_layer = []
        for addr in current_layer:
            if addr.lower() in visited:
                continue
            visited.add(addr.lower())

            txns = get_transactions(addr, api_key, chain_id=chain_id, limit=txns_per_hop)
            for tx in txns:
                to_addr = tx["to"]
                if to_addr:
                    graph_edges.append((addr, to_addr, tx["value"], tx["hash"]))
                    next_layer.append(to_addr)

        current_layer = next_layer
        if not current_layer:
            break 

    return graph_edges