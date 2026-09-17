import requests
import time
from config import BASE_URL, SUPPORTED_CHAINS

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


def _fetch(action, address, api_key, chain_id, limit, extra_params=""):
    url = (
        f"{BASE_URL}?chainid={chain_id}"
        f"&module=account&action={action}&address={address}"
        f"&sort=desc{extra_params}&apikey={api_key}"
    )
    try:
        resp = requests.get(url, timeout=15).json()
    except requests.RequestException as exc:
        print(f"[tracer] network error on {action}: {exc}")
        return []

    if resp.get("status") != "1":
        print(f"[tracer] {action} (chain {chain_id}) -> {resp.get('message')}: {resp.get('result')}")
        return []
    return resp["result"][:limit]


def get_eth_transactions(address, api_key, chain_id=1, limit=10):
    raw = _fetch("txlist", address, api_key, chain_id, limit)
    outgoing = [tx for tx in raw if tx["from"].lower() == address.lower()]

    results = []
    for tx in outgoing:
        tx_type = "eth_transfer" if tx.get("input", "0x") == "0x" else "contract_interaction"
        results.append({
            "from": tx["from"].lower(), "to": (tx["to"] or "").lower(), "value": tx["value"],
            "token": "ETH", "type": tx_type, "tx_hash": tx["hash"],
            "timestamp": int(tx["timeStamp"]), "is_spoofed_token": False,
            "chain_id": chain_id,
            "function_name": tx.get("functionName") or None,
            "method_id": tx.get("methodId") or None,
            "_raw": tx,
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
            "from": tx["from"].lower(), "to": (tx["to"] or "").lower(),
            "value": tx["value"], "value_decimals": decimals,
            "token": symbol, "token_contract": contract_address,
            "type": "erc20_transfer", "tx_hash": tx["hash"],
            "timestamp": int(tx["timeStamp"]), "is_spoofed_token": spoofed,
            "chain_id": chain_id,
            "function_name": None,
            "method_id": None,
            "_raw": tx,
        })
    return results


def get_internal_transactions(address, api_key, chain_id=1, limit=10):
    raw = _fetch("txlistinternal", address, api_key, chain_id, limit)
    outgoing = [tx for tx in raw if tx["from"].lower() == address.lower()]

    results = []
    for tx in outgoing:
        results.append({
            "from": tx["from"].lower(), "to": (tx["to"] or "").lower(), "value": tx["value"],
            "token": "ETH", "type": "internal_transfer",
            "tx_hash": tx.get("hash", ""), "timestamp": int(tx["timeStamp"]),
            "is_spoofed_token": False, "chain_id": chain_id,
            "function_name": None,
            "method_id": None,
            "_raw": tx,
        })
    return results


def get_incoming_transactions(address, api_key, chain_id=1, limit=5):

    raw = _fetch("txlist", address, api_key, chain_id, limit)
    incoming = [tx for tx in raw if tx["to"] and tx["to"].lower() == address.lower()]
    if not incoming:
        return None
    return min(int(tx["timeStamp"]) for tx in incoming)


HOPPABLE_TYPES = {"eth_transfer", "erc20_transfer", "internal_transfer"}


def get_all_transactions(address, api_key, chain_id=1, limit_per_type=5):
    eth = get_eth_transactions(address, api_key, chain_id, limit_per_type)
    tokens = get_token_transactions(address, api_key, chain_id, limit_per_type)
    internal = get_internal_transactions(address, api_key, chain_id, limit_per_type)
    return eth + tokens + internal


def trace_wallet(start_address, api_key, chain_id=1, max_hops=3, limit_per_type=5):

    start_address = start_address.lower()
    all_edges = []
    incoming_timestamps = {}
    current_layer = [start_address]
    visited = set()

    for hop in range(max_hops):
        next_layer = []
        for addr in current_layer:
            if addr.lower() in visited:
                continue
            visited.add(addr.lower())

            if addr.lower() != start_address.lower():
                first_in = get_incoming_transactions(addr, api_key, chain_id)
                if first_in:
                    incoming_timestamps[addr] = first_in

            txns = get_all_transactions(addr, api_key, chain_id, limit_per_type)
            for tx in txns:
                tx["hop"] = hop
                all_edges.append(tx)
                if tx["type"] in HOPPABLE_TYPES and tx["to"]:
                    next_layer.append(tx["to"])

        current_layer = next_layer
        if not current_layer:
            break

    return all_edges, incoming_timestamps


def cross_chain_reuse_check(address, api_key, primary_chain_id=1, other_chains=None):
    """
    Heuristic cross-chain check: many bridges (especially LayerZero-based
    ones like Stargate, and address-preserving message bridges) credit
    the SAME address on the destination chain. This checks whether the
    traced address has any activity on other configured chains at all -
    a lightweight, honest substitute for full bridge event decoding.

    Returns a dict of {chain_name: tx_count} for chains where the address
    has activity, excluding the primary chain.

    LIMITATION (unchanged): this does not match a specific bridge deposit
    to its destination-chain payout — it only tells you the address is
    active elsewhere too. Real bridge-event correlation would need to
    decode each bridge contract's deposit/mint events individually.
    """
    if other_chains is None:
        other_chains = [cid for cid in SUPPORTED_CHAINS if cid != primary_chain_id]

    findings = {}
    for cid in other_chains:
        txns = _fetch("txlist", address, api_key, cid, limit=1)
        if txns:
            findings[SUPPORTED_CHAINS.get(cid, str(cid))] = cid
        time.sleep(0.2)  
    return findings