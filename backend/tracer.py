import os
import time
import threading
import requests
from datetime import datetime

from config import BASE_URL, SUPPORTED_CHAINS


# Maximum unique addresses that can be expanded during one trace.
# This prevents hop-2 / hop-3 fan-out from becoming enormous.
MAX_TRACE_ADDRESSES = int(
    os.getenv("MAX_TRACE_ADDRESSES", "25")
)

# Maximum number of new addresses selected from ONE node for
# recursive expansion.
#
# Important:
# This does NOT remove transactions from the evidence/graph.
# It only limits which destinations are recursively investigated.
MAX_EXPANSION_TARGETS_PER_NODE = int(
    os.getenv("MAX_EXPANSION_TARGETS_PER_NODE", "8")
)

# Hard safety limit on collected edges.
MAX_TRACE_EDGES = int(
    os.getenv("MAX_TRACE_EDGES", "250")
)

# Only perform incoming-history lookups for this many downstream
# addresses. Incoming timestamps are useful for rapid-movement
# detection, but checking every node adds another provider call.
MAX_INCOMING_CHECKS = int(
    os.getenv("MAX_INCOMING_CHECKS", "12")
)

# Etherscan's free tier is commonly rate limited around 3 requests/sec.
# Keep a small spacing between requests made by this process.
ETHERSCAN_MIN_INTERVAL = float(
    os.getenv("ETHERSCAN_MIN_INTERVAL", "0.40")
)

_etherscan_lock = threading.Lock()
_last_etherscan_request = 0.0


KNOWN_REAL_TOKEN_CONTRACTS = {
    "USDT": "0xdac17f958d2ee523a220620006994597c13d831ec7",
    "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "DAI": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "WETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
}



ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_KEY")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
GOLDRUSH_API_KEY = os.getenv("GOLDRUSH_API_KEY")


QUICKNODE_ENDPOINTS = {
    56: os.getenv("QUICKNODE_BSC_URL"),
}


print(
    "[tracer] provider config:",
    {
        "etherscan": bool(ETHERSCAN_API_KEY),
        "alchemy": bool(ALCHEMY_API_KEY),
        "goldrush": bool(GOLDRUSH_API_KEY),
        "quicknode_bsc": bool(
            QUICKNODE_ENDPOINTS.get(56)
        ),
    },
)

print(
    "[tracer] trace limits:",
    {
        "max_addresses": MAX_TRACE_ADDRESSES,
        "max_expansion_per_node": MAX_EXPANSION_TARGETS_PER_NODE,
        "max_edges": MAX_TRACE_EDGES,
        "max_incoming_checks": MAX_INCOMING_CHECKS,
        "etherscan_interval": ETHERSCAN_MIN_INTERVAL,
    },
)


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
    56: "bnb-mainnet",
    137: "polygon-mainnet",
    42161: "arb-mainnet",
    10: "opt-mainnet",
}


def _is_spoofed_token(symbol, contract_address):
    symbol = symbol or ""

    if not symbol.isascii():
        return True

    upper = symbol.upper()

    if upper in KNOWN_REAL_TOKEN_CONTRACTS:
        real_address = KNOWN_REAL_TOKEN_CONTRACTS[upper]

        if (
            contract_address or ""
        ).lower() != real_address.lower():
            return True

    return False


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_address(address):
    return (address or "").lower()


def _parse_timestamp(value):
    if not value:
        return 0

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass

        try:
            return int(
                datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                ).timestamp()
            )
        except ValueError:
            return 0

    return 0


def _wait_for_etherscan_slot():
    """
    Keep Etherscan requests spaced out enough to avoid hammering
    the free API rate limit.

    This is intentionally process-local. It protects a warm Vercel
    instance without adding unnecessary complexity.
    """
    global _last_etherscan_request

    with _etherscan_lock:
        now = time.monotonic()

        elapsed = (
            now - _last_etherscan_request
        )

        if (
            _last_etherscan_request > 0
            and elapsed < ETHERSCAN_MIN_INTERVAL
        ):
            time.sleep(
                ETHERSCAN_MIN_INTERVAL - elapsed
            )

        _last_etherscan_request = time.monotonic()

def _etherscan_fetch(
    action,
    address,
    chain_id,
    limit,
    extra_params="",
    scan_limit=None,
):
    """
    Fetch enough history to avoid dropping outgoing transactions
    hidden by newer incoming transactions.

    Direction/type filtering happens AFTER fetching.
    """

    if not ETHERSCAN_API_KEY:
        print(
            "[tracer] Etherscan API key missing"
        )
        return None

    scan_limit = max(
        int(scan_limit or limit),
        int(limit),
        100,
    )

    url = (
        f"{BASE_URL}"
        f"?chainid={chain_id}"
        f"&module=account"
        f"&action={action}"
        f"&address={address}"
        f"&page=1"
        f"&offset={scan_limit}"
        f"&sort=desc"
        f"{extra_params}"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    _wait_for_etherscan_slot()

    try:
        response = requests.get(
            url,
            timeout=15,
        )

        response.raise_for_status()
        data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        print(
            f"[tracer] Etherscan network error "
            f"on {action} chain={chain_id}: {exc}"
        )
        return None

    if data.get("status") != "1":
        message = data.get("message")
        result_message = data.get("result")

        print(
            f"[tracer] Etherscan {action} "
            f"(chain {chain_id}) -> "
            f"{message}: {result_message}"
        )

        return None

    result = data.get(
        "result",
        [],
    )

    if not isinstance(result, list):
        print(
            f"[tracer] Etherscan {action} "
            f"(chain {chain_id}) returned "
            f"non-list result"
        )

        return None

    print(
        f"[tracer] Etherscan {action} "
        f"chain={chain_id}: "
        f"fetched {len(result)} records"
    )

    return result


def _goldrush_headers():
    if not GOLDRUSH_API_KEY:
        return None

    return {
        "Authorization": (
            f"Bearer {GOLDRUSH_API_KEY}"
        ),
        "Content-Type": "application/json",
    }


def _goldrush_request(
    path,
    params=None,
):
    headers = _goldrush_headers()

    if headers is None:
        print(
            "[tracer] GoldRush API key missing"
        )
        return None

    url = (
        f"https://api.covalenthq.com/v1"
        f"{path}"
    )

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=10,
        )

        if response.status_code >= 400:
            body = response.text[:500]

            print(
                f"[tracer] GoldRush HTTP "
                f"{response.status_code}: "
                f"{body}"
            )

            return None

        payload = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        print(
            f"[tracer] GoldRush network error: "
            f"{exc}"
        )

        return None

    if payload.get("error"):
        print(
            f"[tracer] GoldRush API error: "
            f"{payload.get('error_message')}"
        )

        return None

    return payload


def _goldrush_fetch_transactions(
    address,
    chain_id,
    limit=10,
):
    chain = GOLDRUSH_CHAINS.get(
        chain_id
    )

    if not chain:
        print(
            f"[tracer] GoldRush unsupported "
            f"chain {chain_id}"
        )

        return None

    payload = _goldrush_request(
        f"/{chain}/address/{address}/transactions_v3/",
    )

    if payload is None:
        return None

    items = (
        payload
        .get("data", {})
        .get("items", [])
    )

    if not isinstance(items, list):
        return None

    return items[:limit]


def _goldrush_fetch_activity(
    address,
):
    payload = _goldrush_request(
        f"/address/{address}/activity/"
    )

    if payload is None:
        return None

    items = (
        payload
        .get("data", {})
        .get("items", [])
    )

    if not isinstance(items, list):
        return None

    return items


def _alchemy_rpc(
    chain_id,
    method,
    params,
):
    if not ALCHEMY_API_KEY:
        print(
            "[tracer] Alchemy API key missing"
        )
        return None

    network = ALCHEMY_NETWORKS.get(
        chain_id
    )

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

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        print(
            f"[tracer] Alchemy error "
            f"chain={chain_id}, "
            f"method={method}: {exc}"
        )

        return None

    if "error" in data:
        print(
            f"[tracer] Alchemy RPC error "
            f"chain={chain_id}, "
            f"method={method}: "
            f"{data['error']}"
        )

        return None

    return data.get("result")


def _alchemy_fetch_transfers(
    address,
    chain_id,
    limit=10,
    direction="outgoing",
    categories=None,
):
    if chain_id not in ALCHEMY_NETWORKS:
        return None

    transfers = []
    page_key = None

    if categories is None:
        categories = [
            "external",
            "internal",
            "erc20",
        ]

    try:
        while len(transfers) < limit:
            params = {
                "fromBlock": "0x0",
                "toBlock": "latest",
                "category": categories,
                "withMetadata": True,
                "excludeZeroValue": True,
                "maxCount": hex(
                    min(
                        limit - len(transfers),
                        100,
                    )
                ),
                "order": "desc",
            }

            if direction == "incoming":
                params["toAddress"] = address
            else:
                params["fromAddress"] = address

            if page_key:
                params["pageKey"] = page_key

            result = _alchemy_rpc(
                chain_id,
                "alchemy_getAssetTransfers",
                [params],
            )

            if result is None:
                return None

            batch = result.get(
                "transfers",
                [],
            )

            if not isinstance(batch, list):
                return None

            transfers.extend(batch)

            page_key = result.get(
                "pageKey"
            )

            if not page_key or not batch:
                break

    except Exception as exc:
        print(
            f"[tracer] Alchemy transfer error "
            f"chain={chain_id}: {exc}"
        )

        return None

    return transfers[:limit]


def _quicknode_rpc(
    chain_id,
    method,
    params,
):
    endpoint = QUICKNODE_ENDPOINTS.get(
        chain_id
    )

    if not endpoint:
        print(
            f"[tracer] QuickNode endpoint missing "
            f"for chain={chain_id}"
        )

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

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        print(
            f"[tracer] QuickNode error "
            f"chain={chain_id}, "
            f"method={method}: {exc}"
        )

        return None

    if "error" in data:
        print(
            f"[tracer] QuickNode RPC error "
            f"chain={chain_id}, "
            f"method={method}: "
            f"{data['error']}"
        )

        return None

    return data.get("result")


def _quicknode_block_number(
    chain_id,
):
    return _quicknode_rpc(
        chain_id,
        "eth_blockNumber",
        [],
    )


def _normalize_etherscan_transaction(
    tx,
    chain_id,
):
    from_address = _normalize_address(
        tx.get("from")
    )

    to_address = _normalize_address(
        tx.get("to")
    )

    tx_type = (
        "eth_transfer"
        if tx.get("input", "0x") == "0x"
        else "contract_interaction"
    )

    return {
        "from": from_address,
        "to": to_address,
        "value": tx.get(
            "value",
            "0",
        ),
        "value_decimals": 18,
        "token": "ETH",
        "type": tx_type,
        "tx_hash": tx.get(
            "hash",
            "",
        ),
        "timestamp": _safe_int(
            tx.get("timeStamp")
        ),
        "is_spoofed_token": False,
        "chain_id": chain_id,
        "function_name": (
            tx.get("functionName")
            or None
        ),
        "method_id": (
            tx.get("methodId")
            or None
        ),
        "_raw": tx,
    }


def _normalize_etherscan_token(
    tx,
    chain_id,
):
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
        "from": _normalize_address(
            tx.get("from")
        ),
        "to": _normalize_address(
            tx.get("to")
        ),
        "value": tx.get(
            "value",
            "0",
        ),
        "value_decimals": decimals,
        "token": symbol,
        "token_contract": contract_address,
        "type": "erc20_transfer",
        "tx_hash": tx.get(
            "hash",
            "",
        ),
        "timestamp": _safe_int(
            tx.get("timeStamp")
        ),
        "is_spoofed_token": _is_spoofed_token(
            symbol,
            contract_address,
        ),
        "chain_id": chain_id,
        "function_name": None,
        "method_id": None,
        "_raw": tx,
    }


def _normalize_etherscan_internal(
    tx,
    chain_id,
):
    return {
        "from": _normalize_address(
            tx.get("from")
        ),
        "to": _normalize_address(
            tx.get("to")
        ),
        "value": tx.get(
            "value",
            "0",
        ),
        "value_decimals": 18,
        "token": "ETH",
        "type": "internal_transfer",
        "tx_hash": tx.get(
            "hash",
            "",
        ),
        "timestamp": _safe_int(
            tx.get("timeStamp")
        ),
        "is_spoofed_token": False,
        "chain_id": chain_id,
        "function_name": None,
        "method_id": None,
        "_raw": tx,
    }


def _normalize_goldrush_transaction(
    tx,
    address,
    chain_id,
):
    from_address = _normalize_address(
        tx.get("from_address")
    )

    to_address = _normalize_address(
        tx.get("to_address")
    )

    return {
        "from": from_address,
        "to": to_address,
        "value": str(
            tx.get("value") or "0"
        ),
        "value_decimals": 18,
        "token": "ETH",
        "type": (
            "eth_transfer"
            if from_address == address.lower()
            else "contract_interaction"
        ),
        "tx_hash": tx.get(
            "tx_hash",
            tx.get(
                "tx_hash_hex",
                "",
            ),
        ),
        "timestamp": _parse_timestamp(
            tx.get("block_signed_at")
        ),
        "is_spoofed_token": False,
        "chain_id": chain_id,
        "function_name": (
            tx.get("decoded")
            if isinstance(
                tx.get("decoded"),
                str,
            )
            else None
        ),
        "method_id": tx.get(
            "method_id"
        ),
        "_raw": tx,
    }


def _extract_alchemy_timestamp(
    tx,
):
    metadata = (
        tx.get("metadata")
        or {}
    )

    if isinstance(
        metadata,
        dict,
    ):
        return _parse_timestamp(
            metadata.get(
                "blockTimestamp"
            )
        )

    return 0


def _alchemy_raw_value(
    tx,
):
    raw_contract = (
        tx.get("rawContract")
        or {}
    )

    raw_value = raw_contract.get(
        "value"
    )

    decimals = _safe_int(
        raw_contract.get(
            "decimal"
        ),
        18,
    )

    if raw_value is not None:
        return (
            str(raw_value),
            decimals,
        )

    value = tx.get(
        "value",
        0,
    )

    try:
        raw_value = int(
            round(
                float(value)
                * (10 ** decimals)
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        raw_value = 0

    return (
        str(raw_value),
        decimals,
    )


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

    value, decimals = (
        _alchemy_raw_value(tx)
    )

    if category == "erc20":
        token_type = "erc20_transfer"

    elif category == "internal":
        token_type = "internal_transfer"

    else:
        token_type = "eth_transfer"

    raw_contract = (
        tx.get("rawContract")
        or {}
    )

    contract_address = raw_contract.get(
        "address",
        "",
    )

    return {
        "from": from_address,
        "to": to_address,
        "value": value,
        "value_decimals": decimals,
        "token": asset,
        "token_contract": contract_address,
        "type": token_type,
        "tx_hash": tx.get(
            "hash",
            "",
        ),
        "timestamp": _extract_alchemy_timestamp(
            tx
        ),
        "is_spoofed_token": (
            _is_spoofed_token(
                asset,
                contract_address,
            )
            if category == "erc20"
            else False
        ),
        "chain_id": chain_id,
        "function_name": None,
        "method_id": None,
        "_raw": tx,
    }



def _provider_order(
    chain_id,
):
    if chain_id == 56:
        return [
            "goldrush",
            "alchemy",
            "etherscan",
        ]

    if chain_id == 43114:
        return [
            "goldrush",
            "etherscan",
            "alchemy",
        ]

    return [
        "etherscan",
        "goldrush",
        "alchemy",
    ]




def get_eth_transactions(
    address,
    api_key=None,
    chain_id=1,
    limit=10,
):
    address = address.lower()

    for provider in _provider_order(
        chain_id
    ):

        if provider == "etherscan":
            raw = _etherscan_fetch(
                "txlist",
                address,
                chain_id,
                limit,
            )

            if raw is None:
                continue

            outgoing = [
                tx
                for tx in raw
                if _normalize_address(
                    tx.get("from")
                ) == address
            ]

            print(
                f"[tracer] ETH transactions "
                f"chain={chain_id}: Etherscan "
                f"raw={len(raw)} "
                f"outgoing={len(outgoing)}"
            )

            if outgoing:
                return [
                    _normalize_etherscan_transaction(
                        tx,
                        chain_id,
                    )
                    for tx in outgoing[:limit]
                ]

            continue

        if provider == "goldrush":
            raw = _goldrush_fetch_transactions(
                address,
                chain_id,
                limit,
            )

            if raw is None:
                continue

            print(
                f"[tracer] ETH transactions "
                f"chain={chain_id}: GoldRush"
            )

            transfers = [
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

            if transfers:
                return transfers[:limit]

            continue

        if provider == "alchemy":
            raw = _alchemy_fetch_transfers(
                address,
                chain_id,
                limit,
                direction="outgoing",
                categories=["external"],
            )

            if raw is None:
                continue

            print(
                f"[tracer] ETH transactions "
                f"chain={chain_id}: Alchemy"
            )

            transfers = [
                _normalize_alchemy_transfer(
                    tx,
                    address,
                    chain_id,
                )
                for tx in raw
                if (
                    _normalize_address(
                        tx.get("from")
                    ) == address
                    and tx.get(
                        "category"
                    ) == "external"
                )
            ]

            if transfers:
                return transfers[:limit]

            continue

    return []



def _goldrush_token_transfers(
    address,
    chain_id,
    limit,
):
    raw = _goldrush_fetch_transactions(
        address,
        chain_id,
        limit,
    )

    if raw is None:
        return None

    results = []

    for tx in raw:
        if _normalize_address(
            tx.get("from_address")
        ) != address:
            continue

        timestamp = _parse_timestamp(
            tx.get("block_signed_at")
        )

        events = (
            tx.get("log_events", [])
            or []
        )

        for event in events:
            decoded = (
                event.get("decoded")
                or {}
            )

            if decoded.get(
                "name"
            ) != "Transfer":
                continue

            params = (
                decoded.get("params")
                or []
            )

            from_value = None
            to_value = None
            value = None

            for param in params:
                name = str(
                    param.get(
                        "name",
                        "",
                    )
                ).lower()

                if name == "from":
                    from_value = param.get(
                        "value"
                    )

                elif name == "to":
                    to_value = param.get(
                        "value"
                    )

                elif name == "value":
                    value = param.get(
                        "value"
                    )

            if (
                from_value
                and _normalize_address(
                    from_value
                ) != address
            ):
                continue

            decimals = _safe_int(
                event.get(
                    "sender_contract_decimals"
                ),
                18,
            )

            symbol = (
                event.get(
                    "sender_contract_ticker_symbol"
                )
                or event.get(
                    "sender_name"
                )
                or "UNKNOWN"
            )

            contract = (
                event.get(
                    "sender_address"
                )
                or ""
            )

            results.append(
                {
                    "from": address,
                    "to": _normalize_address(
                        to_value
                        or tx.get(
                            "to_address"
                        )
                    ),
                    "value": str(
                        value or "0"
                    ),
                    "value_decimals": decimals,
                    "token": symbol,
                    "token_contract": contract,
                    "type": "erc20_transfer",
                    "tx_hash": tx.get(
                        "tx_hash",
                        "",
                    ),
                    "timestamp": timestamp,
                    "is_spoofed_token": (
                        _is_spoofed_token(
                            symbol,
                            contract,
                        )
                    ),
                    "chain_id": chain_id,
                    "function_name": None,
                    "method_id": None,
                    "_raw": event,
                }
            )

            if len(results) >= limit:
                break

        if len(results) >= limit:
            break

    return results[:limit]




def get_token_transactions(
    address,
    api_key=None,
    chain_id=1,
    limit=10,
):
    address = address.lower()

    for provider in _provider_order(
        chain_id
    ):

        if provider == "etherscan":
            raw = _etherscan_fetch(
                "tokentx",
                address,
                chain_id,
                limit,
            )

            if raw is None:
                continue

            outgoing = [
                tx
                for tx in raw
                if _normalize_address(
                    tx.get("from")
                ) == address
            ]

            print(
                f"[tracer] ERC20 transactions "
                f"chain={chain_id}: Etherscan "
                f"raw={len(raw)} "
                f"outgoing={len(outgoing)}"
            )

            if outgoing:
                return [
                    _normalize_etherscan_token(
                        tx,
                        chain_id,
                    )
                    for tx in outgoing[:limit]
                ]

            continue

        if provider == "goldrush":
            raw = _goldrush_token_transfers(
                address,
                chain_id,
                limit,
            )

            if raw is None:
                continue

            print(
                f"[tracer] ERC20 transactions "
                f"chain={chain_id}: GoldRush"
            )

            if raw:
                return raw[:limit]

            continue

        if provider == "alchemy":
            raw = _alchemy_fetch_transfers(
                address,
                chain_id,
                limit,
                direction="outgoing",
                categories=["erc20"],
            )

            if raw is None:
                continue

            print(
                f"[tracer] ERC20 transactions "
                f"chain={chain_id}: Alchemy"
            )

            transfers = [
                _normalize_alchemy_transfer(
                    tx,
                    address,
                    chain_id,
                )
                for tx in raw
                if (
                    _normalize_address(
                        tx.get("from")
                    ) == address
                    and tx.get(
                        "category"
                    ) == "erc20"
                )
            ]

            if transfers:
                return transfers[:limit]

            continue

    return []




def get_internal_transactions(
    address,
    api_key=None,
    chain_id=1,
    limit=10,
):
    address = address.lower()

    raw = _etherscan_fetch(
        "txlistinternal",
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        outgoing = [
            tx
            for tx in raw
            if _normalize_address(
                tx.get("from")
            ) == address
        ]

        print(
            f"[tracer] Internal transactions "
            f"chain={chain_id}: Etherscan "
            f"raw={len(raw)} "
            f"outgoing={len(outgoing)}"
        )

        if outgoing:
            return [
                _normalize_etherscan_internal(
                    tx,
                    chain_id,
                )
                for tx in outgoing[:limit]
            ]

    raw = _alchemy_fetch_transfers(
        address,
        chain_id,
        limit,
        direction="outgoing",
        categories=["internal"],
    )

    if raw is not None:
        internal = [
            tx
            for tx in raw
            if (
                tx.get("category")
                == "internal"
                and _normalize_address(
                    tx.get("from")
                ) == address
            )
        ]

        if internal:
            print(
                f"[tracer] Internal transactions "
                f"chain={chain_id}: Alchemy"
            )

            return [
                _normalize_alchemy_transfer(
                    tx,
                    address,
                    chain_id,
                )
                for tx in internal
            ]

    if chain_id == 56:
        block = _quicknode_block_number(
            chain_id
        )

        if block is not None:
            print(
                f"[tracer] QuickNode available "
                f"for lower-level tracing "
                f"chain={chain_id}"
            )

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
            tx
            for tx in raw
            if (
                tx.get("to")
                and _normalize_address(
                    tx.get("to")
                ) == address
            )
        ]

        if incoming:
            timestamps = [
                _safe_int(
                    tx.get("timeStamp")
                )
                for tx in incoming
            ]

            timestamps = [
                timestamp
                for timestamp in timestamps
                if timestamp
            ]

            return (
                min(timestamps)
                if timestamps
                else None
            )

        # IMPORTANT:
        # Do not immediately return None.
        # Etherscan can successfully return history that does not
        # contain an incoming transaction in the scanned batch.
        # Let GoldRush / Alchemy try next.
        print(
            f"[tracer] No incoming Etherscan "
            f"transactions found for {address}; "
            f"trying fallback providers"
        )

  

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

        if incoming:
            timestamps = [
                _parse_timestamp(
                    tx.get(
                        "block_signed_at"
                    )
                )
                for tx in incoming
            ]

            timestamps = [
                timestamp
                for timestamp in timestamps
                if timestamp
            ]

            return (
                min(timestamps)
                if timestamps
                else None
            )

    

    raw = _alchemy_fetch_transfers(
        address,
        chain_id,
        limit,
        direction="incoming",
        categories=[
            "external",
            "internal",
            "erc20",
        ],
    )

    if raw is not None:
        incoming = [
            tx
            for tx in raw
            if _normalize_address(
                tx.get("to")
            ) == address
        ]

        if incoming:
            timestamps = [
                _extract_alchemy_timestamp(
                    tx
                )
                for tx in incoming
            ]

            timestamps = [
                timestamp
                for timestamp in timestamps
                if timestamp
            ]

            return (
                min(timestamps)
                if timestamps
                else None
            )

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

    transactions = (
        eth
        + tokens
        + internal
    )

    # Remove exact duplicate transactions when multiple provider
    # paths expose the same hash/type/destination.
    #
    # This does NOT remove different token transfers from the same
    # transaction because the token contract remains part of the key.
    unique = []
    seen = set()

    for tx in transactions:
        key = (
            tx.get("tx_hash"),
            tx.get("type"),
            tx.get("to"),
            tx.get("token_contract"),
        )

        if (
            key in seen
            and key[0]
        ):
            continue

        seen.add(key)
        unique.append(tx)

    return unique




def _expansion_targets(
    addr,
    transactions,
    visited,
):
    """
    Select destinations for recursive tracing.

    Important design choice:

    contract_interaction edges are recorded in the graph/evidence,
    but are NOT recursively expanded by default.

    Otherwise an ordinary wallet interaction with a smart contract
    can cause CITRUS to start treating the contract as another wallet
    and explode the graph.

    ERC20 / ETH / internal transfers remain expandable.
    """

    candidates = []

    for tx in transactions:
        tx_type = tx.get(
            "type"
        )

        if tx_type not in HOPPABLE_TYPES:
            continue

        target = _normalize_address(
            tx.get("to")
        )

        if not target:
            continue

        if target == addr:
            continue

        if target in visited:
            continue

        candidates.append(target)

    # Preserve transaction ordering while removing duplicates.
    candidates = list(
        dict.fromkeys(candidates)
    )

    return candidates[
        :MAX_EXPANSION_TARGETS_PER_NODE
    ]




def trace_wallet(
    start_address,
    api_key=None,
    chain_id=1,
    max_hops=3,
    limit_per_type=5,
):
    """
    Trace a wallet using bounded breadth-first expansion.

    max_hops remains user-configurable.

    Safety limits prevent:
      - enormous fan-out
      - repeated address expansion
      - recursive contract expansion
      - excessive provider requests
      - Vercel function timeouts

    All discovered transactions from processed addresses remain
    in all_edges. The expansion limits only determine which
    destinations receive further recursive investigation.
    """

    start_address = (
        start_address.lower()
    )

    all_edges = []
    incoming_timestamps = {}

    current_layer = [
        start_address
    ]

    visited = set()

    incoming_checks = 0

    print(
        "[tracer] starting trace:",
        {
            "address": start_address,
            "chain": chain_id,
            "max_hops": max_hops,
            "limit_per_type": limit_per_type,
            "max_addresses": MAX_TRACE_ADDRESSES,
            "max_edges": MAX_TRACE_EDGES,
            "max_expansion_per_node": (
                MAX_EXPANSION_TARGETS_PER_NODE
            ),
        },
    )

    for hop in range(
        max_hops
    ):
        if not current_layer:
            break

        print(
            f"[tracer] ===== hop {hop} "
            f"addresses={len(current_layer)} ====="
        )

        next_layer = []

        for addr in current_layer:
            addr = _normalize_address(
                addr
            )

            if not addr:
                continue

            if addr in visited:
                continue

            if len(visited) >= MAX_TRACE_ADDRESSES:
                print(
                    "[tracer] address budget reached: "
                    f"{MAX_TRACE_ADDRESSES}"
                )
                break

            visited.add(addr)

            print(
                f"[tracer] tracing address "
                f"{addr} "
                f"hop={hop} "
                f"visited={len(visited)}/"
                f"{MAX_TRACE_ADDRESSES}"
            )

           

            if (
                addr != start_address
                and incoming_checks
                < MAX_INCOMING_CHECKS
            ):
                first_in = (
                    get_incoming_transactions(
                        addr,
                        api_key,
                        chain_id,
                    )
                )

                incoming_checks += 1

                if first_in:
                    incoming_timestamps[
                        addr
                    ] = first_in

           

            txns = get_all_transactions(
                addr,
                api_key,
                chain_id,
                limit_per_type,
            )

            print(
                f"[tracer] address {addr}: "
                f"{len(txns)} transaction(s)"
            )

          

            remaining_edges = (
                MAX_TRACE_EDGES
                - len(all_edges)
            )

            if remaining_edges <= 0:
                print(
                    "[tracer] edge budget reached: "
                    f"{MAX_TRACE_EDGES}"
                )
                break

            txns_to_store = txns[
                :remaining_edges
            ]

            for tx in txns_to_store:
                tx["hop"] = hop
                all_edges.append(tx)

            if (
                len(all_edges)
                >= MAX_TRACE_EDGES
            ):
                print(
                    "[tracer] edge budget reached "
                    f"at {MAX_TRACE_EDGES}"
                )
                break

          

            targets = _expansion_targets(
                addr,
                txns,
                visited,
            )

            if targets:
                print(
                    f"[tracer] expansion from "
                    f"{addr}: "
                    f"{len(targets)} target(s)"
                )

                next_layer.extend(
                    targets
                )

            else:
                print(
                    f"[tracer] no expandable "
                    f"targets from {addr}"
                )

        

        if (
            len(visited)
            >= MAX_TRACE_ADDRESSES
        ):
            print(
                "[tracer] stopping expansion: "
                "maximum address budget reached"
            )
            break

        next_layer = list(
            dict.fromkeys(
                next_layer
            )
        )

        # Do not queue addresses already visited.
        next_layer = [
            addr
            for addr in next_layer
            if addr not in visited
        ]

        # Hard cap the next frontier so a single high-fanout
        # layer cannot create an enormous queue.
        remaining_address_budget = (
            MAX_TRACE_ADDRESSES
            - len(visited)
        )

        if remaining_address_budget <= 0:
            break

        next_layer = next_layer[
            :remaining_address_budget
        ]

        print(
            f"[tracer] hop {hop} complete: "
            f"next_layer={len(next_layer)}, "
            f"visited={len(visited)}, "
            f"edges={len(all_edges)}"
        )

        current_layer = next_layer

        if not current_layer:
            print(
                "[tracer] trace finished: "
                "no more expandable addresses"
            )
            break

        if (
            len(all_edges)
            >= MAX_TRACE_EDGES
        ):
            print(
                "[tracer] trace finished: "
                "maximum edge budget reached"
            )
            break

    print(
        "[tracer] trace complete:",
        {
            "addresses_visited": len(visited),
            "edges": len(all_edges),
            "incoming_checks": incoming_checks,
            "max_hops": max_hops,
        },
    )

    return (
        all_edges,
        incoming_timestamps,
    )




def _chain_id_from_activity(
    item,
):
    value = item.get(
        "chain_id"
    )

    if value is not None:
        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            pass

    chain_name = (
        item.get("chain_name")
        or item.get("chain")
        or ""
    )

    chain_name = str(
        chain_name
    ).lower()

    for cid, slug in (
        GOLDRUSH_CHAINS.items()
    ):
        if chain_name == slug:
            return cid

    return None


def _goldrush_cross_chain_activity(
    address,
    primary_chain_id,
):
    activity = (
        _goldrush_fetch_activity(
            address
        )
    )

    if activity is None:
        return None

    findings = {}

    for item in activity:
        cid = _chain_id_from_activity(
            item
        )

        if cid is None:
            continue

        if cid == primary_chain_id:
            continue

        if cid not in SUPPORTED_CHAINS:
            continue

        chain_name = (
            SUPPORTED_CHAINS[cid]
        )

        findings[
            chain_name
        ] = cid

    return findings




def cross_chain_reuse_check(
    address,
    api_key=None,
    primary_chain_id=1,
    other_chains=None,
):
    print(
        "[cross-chain] provider order:",
        {
            cid: _provider_order(cid)
            for cid in SUPPORTED_CHAINS
            if cid != primary_chain_id
        },
    )

    address = address.lower()

    if other_chains is None:
        other_chains = [
            cid
            for cid in SUPPORTED_CHAINS
            if cid != primary_chain_id
        ]

    findings = {}

   

    if GOLDRUSH_API_KEY:
        activity = (
            _goldrush_cross_chain_activity(
                address,
                primary_chain_id,
            )
        )

        if activity is not None:
            findings.update(
                activity
            )

            for cid in other_chains:
                chain_name = (
                    SUPPORTED_CHAINS.get(
                        cid,
                        str(cid),
                    )
                )

                if cid in activity.values():
                    print(
                        f"[cross-chain] "
                        f"{chain_name}: "
                        f"GoldRush activity "
                        f"detected"
                    )
                else:
                    print(
                        f"[cross-chain] "
                        f"{chain_name}: "
                        f"GoldRush checked"
                    )

            return findings

   

    for cid in other_chains:
        chain_name = (
            SUPPORTED_CHAINS.get(
                cid,
                str(cid),
            )
        )

        providers = _provider_order(
            cid
        )

        checked = False

        for provider in providers:

          

            if provider == "goldrush":
                raw = (
                    _goldrush_fetch_transactions(
                        address,
                        cid,
                        limit=1,
                    )
                )

                if raw is None:
                    continue

                checked = True

                if raw:
                    findings[
                        chain_name
                    ] = cid

                print(
                    f"[cross-chain] "
                    f"{chain_name}: "
                    f"GoldRush checked"
                )

                break


            if provider == "etherscan":
                raw = _etherscan_fetch(
                    "txlist",
                    address,
                    cid,
                    limit=1,
                )

                if raw is None:
                    continue

                checked = True

                if raw:
                    findings[
                        chain_name
                    ] = cid

                print(
                    f"[cross-chain] "
                    f"{chain_name}: "
                    f"Etherscan checked"
                )

                break

            if provider == "alchemy":
                raw = (
                    _alchemy_fetch_transfers(
                        address,
                        cid,
                        limit=1,
                        direction="outgoing",
                        categories=[
                            "external"
                        ],
                    )
                )

                if raw is None:
                    continue

                checked = True

                if raw:
                    findings[
                        chain_name
                    ] = cid

                print(
                    f"[cross-chain] "
                    f"{chain_name}: "
                    f"Alchemy checked"
                )

                break

        if checked:
            continue

        if cid in QUICKNODE_ENDPOINTS:
            block = (
                _quicknode_block_number(
                    cid
                )
            )

            if block is not None:
                print(
                    f"[cross-chain] "
                    f"{chain_name}: "
                    f"QuickNode reachable, "
                    f"but no indexed history "
                    f"provider succeeded"
                )

            else:
                print(
                    f"[cross-chain] "
                    f"{chain_name}: "
                    f"all providers unavailable"
                )

        else:
            print(
                f"[cross-chain] "
                f"{chain_name}: "
                f"all indexed providers "
                f"unavailable"
            )

    return findings