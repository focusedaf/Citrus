import os
import requests
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


ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_KEY")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
GOLDRUSH_API_KEY = os.getenv("GOLDRUSH_API_KEY")

QUICKNODE_ENDPOINTS = {
    56: os.getenv("QUICKNODE_BSC_URL"),
}


GOLDRUSH_CHAINS = {
    1: "eth-mainnet",
    56: "bsc-mainnet",
    137: "matic-mainnet",
    42161: "arbitrum-mainnet",
    10: "optimism-mainnet",
    43114: "avalanche-mainnet",
}


ALCHEMY_NETWORKS = {
    1: "eth-mainnet",
    137: "polygon-mainnet",
    42161: "arb-mainnet",
    10: "opt-mainnet",
}


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_address(address):
    return (address or "").lower()




def _etherscan_fetch(
    action,
    address,
    chain_id,
    limit,
    extra_params="",
):
    """
    Fetch indexed account data from Etherscan V2.

    Returns:
        list | None

    None means:
        Etherscan could not provide the requested data.

    [] means:
        Etherscan successfully answered but there were no records.
    """

    if not ETHERSCAN_API_KEY:
        print("[tracer] Etherscan API key missing")
        return None

    url = (
        f"{BASE_URL}"
        f"?chainid={chain_id}"
        f"&module=account"
        f"&action={action}"
        f"&address={address}"
        f"&sort=desc"
        f"{extra_params}"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError) as exc:
        print(
            f"[tracer] Etherscan network error "
            f"on {action} chain={chain_id}: {exc}"
        )
        return None

    if data.get("status") != "1":
        print(
            f"[tracer] Etherscan {action} "
            f"(chain {chain_id}) -> "
            f"{data.get('message')}: {data.get('result')}"
        )
        return None

    result = data.get("result", [])

    if not isinstance(result, list):
        return None

    return result[:limit]




def _goldrush_fetch_transactions(
    address,
    chain_id,
    limit=10,
):
    """
    GoldRush indexed transaction history.

    GoldRush transactions_v3 gives us transaction-level data
    and decoded log events.
    """

    if not GOLDRUSH_API_KEY:
        return None

    chain = GOLDRUSH_CHAINS.get(chain_id)

    if not chain:
        return None

    url = (
        f"https://api.covalenthq.com/v1/"
        f"{chain}/address/{address}/transactions_v3/"
    )

    headers = {
        "Authorization": f"Bearer {GOLDRUSH_API_KEY}",
        "Content-Type": "application/json",
    }

    params = {
        "no-logs": "false",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()

    except (requests.RequestException, ValueError) as exc:
        print(
            f"[tracer] GoldRush error "
            f"chain={chain_id}: {exc}"
        )
        return None

    if payload.get("error"):
        print(
            f"[tracer] GoldRush API error "
            f"chain={chain_id}: "
            f"{payload.get('error_message')}"
        )
        return None

    items = payload.get("data", {}).get("items", [])

    if not isinstance(items, list):
        return None

    return items[:limit]



def _alchemy_rpc(
    chain_id,
    method,
    params,
):
    """
    Generic Alchemy JSON-RPC request.
    """

    if not ALCHEMY_API_KEY:
        return None

    network = ALCHEMY_NETWORKS.get(chain_id)

    if not network:
        return None

    url = (
        f"https://{network}.g.alchemy.com/v2/"
        f"{ALCHEMY_API_KEY}"
    )

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError) as exc:
        print(
            f"[tracer] Alchemy error "
            f"chain={chain_id}, method={method}: {exc}"
        )
        return None

    if "error" in data:
        print(
            f"[tracer] Alchemy RPC error "
            f"chain={chain_id}, method={method}: "
            f"{data['error']}"
        )
        return None

    return data.get("result")


def _alchemy_fetch_transfers(
    address,
    chain_id,
    limit=10,
):
    """
    Alchemy Transfers API.

    Used for indexed wallet transfer history on chains
    supported by Alchemy's Transfers API.
    """

    if chain_id not in ALCHEMY_NETWORKS:
        return None

    categories = [
        "external",
        "erc20",
    ]

    result = _alchemy_rpc(
        chain_id,
        "alchemy_getAssetTransfers",
        [
            {
                "fromBlock": "0x0",
                "toBlock": "latest",
                "fromAddress": address,
                "category": categories,
                "withMetadata": True,
                "excludeZeroValue": True,
                "maxCount": hex(limit),
                "order": "desc",
            }
        ],
    )

    if result is None:
        return None

    return result.get("transfers", [])




def _quicknode_rpc(
    chain_id,
    method,
    params,
):
    """
    Generic QuickNode JSON-RPC request.

    Currently configured for BSC (chain 56).
    """

    endpoint = QUICKNODE_ENDPOINTS.get(chain_id)

    if not endpoint:
        return None

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError) as exc:
        print(
            f"[tracer] QuickNode error "
            f"chain={chain_id}, method={method}: {exc}"
        )
        return None

    if "error" in data:
        print(
            f"[tracer] QuickNode RPC error "
            f"chain={chain_id}, method={method}: "
            f"{data['error']}"
        )
        return None

    return data.get("result")


def _quicknode_block_number(chain_id):
    return _quicknode_rpc(
        chain_id,
        "eth_blockNumber",
        [],
    )



def _normalize_etherscan_transaction(tx, chain_id):
    from_address = _normalize_address(tx.get("from"))
    to_address = _normalize_address(tx.get("to"))

    tx_type = (
        "eth_transfer"
        if tx.get("input", "0x") == "0x"
        else "contract_interaction"
    )

    return {
        "from": from_address,
        "to": to_address,
        "value": tx.get("value", "0"),
        "token": "ETH",
        "type": tx_type,
        "tx_hash": tx.get("hash", ""),
        "timestamp": _safe_int(tx.get("timeStamp")),
        "is_spoofed_token": False,
        "chain_id": chain_id,
        "function_name": tx.get("functionName") or None,
        "method_id": tx.get("methodId") or None,
        "_raw": tx,
    }


def _normalize_etherscan_token(tx, chain_id):
    decimals = _safe_int(
        tx.get("tokenDecimal"),
        18,
    )

    symbol = tx.get(
        "tokenSymbol",
        "UNKNOWN",
    )

    contract_address = tx.get(
        "contractAddress",
        "",
    )

    return {
        "from": _normalize_address(tx.get("from")),
        "to": _normalize_address(tx.get("to")),
        "value": tx.get("value", "0"),
        "value_decimals": decimals,
        "token": symbol,
        "token_contract": contract_address,
        "type": "erc20_transfer",
        "tx_hash": tx.get("hash", ""),
        "timestamp": _safe_int(tx.get("timeStamp")),
        "is_spoofed_token": _is_spoofed_token(
            symbol,
            contract_address,
        ),
        "chain_id": chain_id,
        "function_name": None,
        "method_id": None,
        "_raw": tx,
    }


def _normalize_etherscan_internal(tx, chain_id):
    return {
        "from": _normalize_address(tx.get("from")),
        "to": _normalize_address(tx.get("to")),
        "value": tx.get("value", "0"),
        "token": "ETH",
        "type": "internal_transfer",
        "tx_hash": tx.get("hash", ""),
        "timestamp": _safe_int(tx.get("timeStamp")),
        "is_spoofed_token": False,
        "chain_id": chain_id,
        "function_name": None,
        "method_id": None,
        "_raw": tx,
    }


def _normalize_goldrush_transaction(tx, address, chain_id):
    """
    Convert GoldRush transaction structure into CITRUS format.

    GoldRush's transaction object can contain decoded log_events,
    so we preserve the complete original object in _raw.
    """

    from_address = _normalize_address(
        tx.get("from_address")
    )

    to_address = _normalize_address(
        tx.get("to_address")
    )

    value = tx.get("value", "0")

    timestamp = tx.get(
        "block_signed_at"
    )

    if isinstance(timestamp, str):
        try:
            from datetime import datetime

            timestamp = int(
                datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                ).timestamp()
            )
        except ValueError:
            timestamp = 0

    return {
        "from": from_address,
        "to": to_address,
        "value": str(value or "0"),
        "token": "ETH",
        "type": (
            "eth_transfer"
            if from_address == address.lower()
            else "contract_interaction"
        ),
        "tx_hash": tx.get(
            "tx_hash",
            tx.get("tx_hash_hex", ""),
        ),
        "timestamp": timestamp or 0,
        "is_spoofed_token": False,
        "chain_id": chain_id,
        "function_name": tx.get("decoded"),
        "method_id": None,
        "_raw": tx,
    }


def _normalize_alchemy_transfer(
    tx,
    address,
    chain_id,
):
    from_address = _normalize_address(
        tx.get("from")
    )

    to_address = _normalize_address(
        tx.get("to")
    )

    category = tx.get(
        "category",
        "external",
    )

    asset = tx.get(
        "asset",
        "ETH",
    )

    raw_value = tx.get(
        "value",
        0,
    )

    token_type = (
        "erc20_transfer"
        if category == "erc20"
        else "eth_transfer"
    )

    return {
        "from": from_address,
        "to": to_address,
        "value": str(raw_value),
        "token": asset,
        "type": token_type,
        "tx_hash": tx.get("hash", ""),
        "timestamp": 0,
        "is_spoofed_token": False,
        "chain_id": chain_id,
        "function_name": None,
        "method_id": None,
        "_raw": tx,
    }




def get_eth_transactions(
    address,
    api_key=None,
    chain_id=1,
    limit=10,
):
    """
    Provider priority:

    1. Etherscan
    2. GoldRush
    3. Alchemy
    """

    address = address.lower()

   

    raw = _etherscan_fetch(
        "txlist",
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        print(
            f"[tracer] ETH transactions "
            f"chain={chain_id}: Etherscan"
        )

        outgoing = [
            tx for tx in raw
            if _normalize_address(tx.get("from")) == address
        ]

        return [
            _normalize_etherscan_transaction(
                tx,
                chain_id,
            )
            for tx in outgoing
        ]

  

    raw = _goldrush_fetch_transactions(
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        print(
            f"[tracer] ETH transactions "
            f"chain={chain_id}: GoldRush"
        )

        return [
            _normalize_goldrush_transaction(
                tx,
                address,
                chain_id,
            )
            for tx in raw
            if _normalize_address(
                tx.get("from_address")
            ) == address
        ]

 
    raw = _alchemy_fetch_transfers(
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        print(
            f"[tracer] ETH transactions "
            f"chain={chain_id}: Alchemy"
        )

        return [
            _normalize_alchemy_transfer(
                tx,
                address,
                chain_id,
            )
            for tx in raw
            if (
                _normalize_address(tx.get("from"))
                == address
                and tx.get("category") == "external"
            )
        ]

    return []


def get_token_transactions(
    address,
    api_key=None,
    chain_id=1,
    limit=10,
):
    """
    Provider priority:

    1. Etherscan
    2. GoldRush transaction history
    3. Alchemy Transfers API
    """

    address = address.lower()

    # Etherscan
    raw = _etherscan_fetch(
        "tokentx",
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        print(
            f"[tracer] ERC20 transactions "
            f"chain={chain_id}: Etherscan"
        )

        outgoing = [
            tx for tx in raw
            if _normalize_address(tx.get("from")) == address
        ]

        return [
            _normalize_etherscan_token(
                tx,
                chain_id,
            )
            for tx in outgoing
        ]

    # Alchemy
    raw = _alchemy_fetch_transfers(
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        print(
            f"[tracer] ERC20 transactions "
            f"chain={chain_id}: Alchemy"
        )

        return [
            _normalize_alchemy_transfer(
                tx,
                address,
                chain_id,
            )
            for tx in raw
            if (
                _normalize_address(tx.get("from"))
                == address
                and tx.get("category") == "erc20"
            )
        ]

    # GoldRush
    raw = _goldrush_fetch_transactions(
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        print(
            f"[tracer] ERC20 fallback "
            f"chain={chain_id}: GoldRush"
        )

        results = []

        for tx in raw:
            if _normalize_address(
                tx.get("from_address")
            ) != address:
                continue

            for event in tx.get(
                "log_events",
                [],
            ) or []:

                decoded = event.get(
                    "decoded"
                ) or {}

                if decoded.get("name") != "Transfer":
                    continue

                results.append({
                    "from": address,
                    "to": _normalize_address(
                        decoded.get("params", [{}])[1].get("value")
                        if len(decoded.get("params", [])) > 1
                        else tx.get("to_address")
                    ),
                    "value": "0",
                    "value_decimals": 18,
                    "token": event.get(
                        "sender_name",
                        "UNKNOWN",
                    ),
                    "token_contract": event.get(
                        "sender_address",
                        "",
                    ),
                    "type": "erc20_transfer",
                    "tx_hash": tx.get(
                        "tx_hash",
                        "",
                    ),
                    "timestamp": 0,
                    "is_spoofed_token": False,
                    "chain_id": chain_id,
                    "function_name": None,
                    "method_id": None,
                    "_raw": event,
                })

        return results[:limit]

    return []


def get_internal_transactions(
    address,
    api_key=None,
    chain_id=1,
    limit=10,
):
    """
    Internal transfers are provider-dependent.

    Etherscan remains the primary source.
    GoldRush transaction data is the fallback.
    QuickNode is reserved for lower-level tracing.
    """

    address = address.lower()

    raw = _etherscan_fetch(
        "txlistinternal",
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        print(
            f"[tracer] Internal transactions "
            f"chain={chain_id}: Etherscan"
        )

        outgoing = [
            tx for tx in raw
            if _normalize_address(tx.get("from")) == address
        ]

        return [
            _normalize_etherscan_internal(
                tx,
                chain_id,
            )
            for tx in outgoing
        ]

    # For now, don't fabricate internal transactions from RPC.
    # QuickNode's Trace API will be integrated here once we
    # implement transaction-level tracing.

    return []


def get_incoming_transactions(
    address,
    api_key=None,
    chain_id=1,
    limit=5,
):
    address = address.lower()

    raw = _etherscan_fetch(
        "txlist",
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        incoming = [
            tx for tx in raw
            if tx.get("to")
            and _normalize_address(tx.get("to")) == address
        ]

        if not incoming:
            return None

        return min(
            _safe_int(tx.get("timeStamp"))
            for tx in incoming
        )

    # GoldRush fallback
    raw = _goldrush_fetch_transactions(
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        incoming = [
            tx
            for tx in raw
            if _normalize_address(
                tx.get("to_address")
            ) == address
        ]

        if not incoming:
            return None

        timestamps = []

        for tx in incoming:
            timestamp = tx.get(
                "block_signed_at"
            )

            if isinstance(timestamp, str):
                try:
                    from datetime import datetime

                    timestamp = int(
                        datetime.fromisoformat(
                            timestamp.replace(
                                "Z",
                                "+00:00",
                            )
                        ).timestamp()
                    )
                except ValueError:
                    continue

            if timestamp:
                timestamps.append(timestamp)

        return min(timestamps) if timestamps else None

    return None




HOPPABLE_TYPES = {
    "eth_transfer",
    "erc20_transfer",
    "internal_transfer",
}


def get_all_transactions(
    address,
    api_key=None,
    chain_id=1,
    limit_per_type=5,
):
    eth = get_eth_transactions(
        address,
        api_key,
        chain_id,
        limit_per_type,
    )

    tokens = get_token_transactions(
        address,
        api_key,
        chain_id,
        limit_per_type,
    )

    internal = get_internal_transactions(
        address,
        api_key,
        chain_id,
        limit_per_type,
    )

    return eth + tokens + internal


def trace_wallet(
    start_address,
    api_key=None,
    chain_id=1,
    max_hops=3,
    limit_per_type=5,
):
    start_address = start_address.lower()

    all_edges = []
    incoming_timestamps = {}

    current_layer = [
        start_address
    ]

    visited = set()

    for hop in range(max_hops):
        next_layer = []

        for addr in current_layer:

            addr = addr.lower()

            if addr in visited:
                continue

            visited.add(addr)

            if addr != start_address:
                first_in = get_incoming_transactions(
                    addr,
                    api_key,
                    chain_id,
                )

                if first_in:
                    incoming_timestamps[addr] = first_in

            txns = get_all_transactions(
                addr,
                api_key,
                chain_id,
                limit_per_type,
            )

            for tx in txns:

                tx["hop"] = hop

                all_edges.append(tx)

                if (
                    tx["type"] in HOPPABLE_TYPES
                    and tx["to"]
                ):
                    next_layer.append(
                        tx["to"].lower()
                    )

        current_layer = list(
            dict.fromkeys(next_layer)
        )

        if not current_layer:
            break

    return all_edges, incoming_timestamps




def cross_chain_reuse_check(
    address,
    api_key=None,
    primary_chain_id=1,
    other_chains=None,
):
    """
    Check whether the address has activity on other chains.

    Provider priority:
        1. GoldRush
        2. Etherscan
        3. Alchemy
        4. QuickNode basic connectivity

    Important:
        QuickNode RPC alone cannot efficiently answer
        "give me every transaction for this address".
        It is therefore a connectivity / lower-level fallback,
        not an indexed transaction-history substitute.
    """

    address = address.lower()

    if other_chains is None:
        other_chains = [
            cid
            for cid in SUPPORTED_CHAINS
            if cid != primary_chain_id
        ]

    findings = {}

    for cid in other_chains:

        chain_name = SUPPORTED_CHAINS.get(
            cid,
            str(cid),
        )

       

        raw = _goldrush_fetch_transactions(
            address,
            cid,
            limit=1,
        )

        if raw is not None:

            if raw:
                findings[chain_name] = cid

            print(
                f"[cross-chain] {chain_name}: "
                f"GoldRush checked"
            )

            continue


        raw = _etherscan_fetch(
            "txlist",
            address,
            cid,
            limit=1,
        )

        if raw is not None:

            if raw:
                findings[chain_name] = cid

            print(
                f"[cross-chain] {chain_name}: "
                f"Etherscan checked"
            )

            continue

       

        raw = _alchemy_fetch_transfers(
            address,
            cid,
            limit=1,
        )

        if raw is not None:

            if raw:
                findings[chain_name] = cid

            print(
                f"[cross-chain] {chain_name}: "
                f"Alchemy checked"
            )

            continue


        if cid in QUICKNODE_ENDPOINTS:

            block = _quicknode_block_number(cid)

            if block is not None:
                print(
                    f"[cross-chain] {chain_name}: "
                    f"QuickNode reachable"
                )

        
            else:
                print(
                    f"[cross-chain] {chain_name}: "
                    f"all providers unavailable"
                )

        else:
            print(
                f"[cross-chain] {chain_name}: "
                f"no indexed provider available"
            )

    return findings