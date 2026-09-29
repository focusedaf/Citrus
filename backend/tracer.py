import os
import requests
from datetime import datetime

from config import BASE_URL, SUPPORTED_CHAINS


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

        if (contract_address or "").lower() != real_address.lower():
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


def _etherscan_fetch(
    action,
    address,
    chain_id,
    limit,
    extra_params="",
):
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
        response = requests.get(
            url,
            timeout=ALCHEMY_TIMEOUT,
        )
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
            f"{data.get('message')}: "
            f"{data.get('result')}"
        )
        return None

    result = data.get("result", [])

    if not isinstance(result, list):
        return None

    return result[:limit]


def _goldrush_headers():
    if not GOLDRUSH_API_KEY:
        return None

    return {
        "Authorization": f"Bearer {GOLDRUSH_API_KEY}",
        "Content-Type": "application/json",
    }


def _goldrush_request(
    path,
    params=None,
):
    global _goldrush_disabled_until

    headers = _goldrush_headers()

    if headers is None:
        print("[tracer] GoldRush API key missing")
        return None

    with _goldrush_lock:
        if time.monotonic() < _goldrush_disabled_until:
            print("[tracer] GoldRush temporarily cooling down")
            return None

    url = f"https://api.covalenthq.com/v1{path}"

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=GOLDRUSH_TIMEOUT,
        )

        if response.status_code >= 500:
            print(
                f"[tracer] GoldRush HTTP {response.status_code}; cooling down"
            )
            with _goldrush_lock:
                _goldrush_disabled_until = (
                    time.monotonic() + GOLDRUSH_COOLDOWN
                )
            return None

        if response.status_code >= 400:
            print(
                f"[tracer] GoldRush HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
            return None

        payload = response.json()

    except requests.Timeout as exc:
        print(f"[tracer] GoldRush timeout: {exc}; cooling down")
        with _goldrush_lock:
            _goldrush_disabled_until = (
                time.monotonic() + GOLDRUSH_COOLDOWN
            )
        return None

    except (requests.RequestException, ValueError) as exc:
        print(f"[tracer] GoldRush network error: {exc}")
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
    chain = GOLDRUSH_CHAINS.get(chain_id)

    if not chain:
        print(
            f"[tracer] GoldRush unsupported chain "
            f"{chain_id}"
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


def _goldrush_fetch_activity(address):
    payload = _goldrush_request(
        f"/address/{address}/activity/",
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
        print("[tracer] Alchemy API key missing")
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
            timeout=QUICKNODE_TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError) as exc:
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
):
    if chain_id not in ALCHEMY_NETWORKS:
        return None

    transfers = []
    page_key = None

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
    endpoint = QUICKNODE_ENDPOINTS.get(chain_id)

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

    except (requests.RequestException, ValueError) as exc:
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


def _quicknode_block_number(chain_id):
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
        "value": tx.get("value", "0"),
        "value_decimals": 18,
        "token": "ETH",
        "type": tx_type,
        "tx_hash": tx.get("hash", ""),
        "timestamp": _safe_int(
            tx.get("timeStamp")
        ),
        "is_spoofed_token": False,
        "chain_id": chain_id,
        "function_name": (
            tx.get("functionName") or None
        ),
        "method_id": (
            tx.get("methodId") or None
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


def _extract_alchemy_timestamp(tx):
    metadata = tx.get(
        "metadata"
    ) or {}

    if isinstance(metadata, dict):
        return _parse_timestamp(
            metadata.get(
                "blockTimestamp"
            )
        )

    return 0


def _alchemy_raw_value(tx):
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

    except (TypeError, ValueError):
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
            "alchemy",
            "etherscan",
        ]

    return [
        "etherscan",
        "alchemy",
        "goldrush",
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

            print(
                f"[tracer] ETH transactions "
                f"chain={chain_id}: "
                f"Etherscan"
            )

            outgoing = [
                tx
                for tx in raw
                if _normalize_address(
                    tx.get("from")
                ) == address
            ]

            return [
                _normalize_etherscan_transaction(
                    tx,
                    chain_id,
                )
                for tx in outgoing
            ]

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
                f"chain={chain_id}: "
                f"GoldRush"
            )

            return [
                _normalize_goldrush_transaction(
                    tx,
                    address,
                    chain_id,
                )
                for tx in raw
                if _normalize_address(
                    tx.get(
                        "from_address"
                    )
                ) == address
            ]

        if provider == "alchemy":
            raw = _alchemy_fetch_transfers(
                address,
                chain_id,
                limit,
                direction="outgoing",
            )

            if raw is None:
                continue

            print(
                f"[tracer] ETH transactions "
                f"chain={chain_id}: "
                f"Alchemy"
            )

            return [
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
                    ) in {
                        "external",
                        "internal",
                    }
                )
            ]

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

        events = tx.get(
            "log_events",
            [],
        ) or []

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
                decoded.get(
                    "params"
                )
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

            print(
                f"[tracer] ERC20 transactions "
                f"chain={chain_id}: "
                f"Etherscan"
            )

            outgoing = [
                tx
                for tx in raw
                if _normalize_address(
                    tx.get("from")
                ) == address
            ]

            return [
                _normalize_etherscan_token(
                    tx,
                    chain_id,
                )
                for tx in outgoing
            ]

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
                f"chain={chain_id}: "
                f"GoldRush"
            )

            return raw

        if provider == "alchemy":
            raw = _alchemy_fetch_transfers(
                address,
                chain_id,
                limit,
                direction="outgoing",
            )

            if raw is None:
                continue

            print(
                f"[tracer] ERC20 transactions "
                f"chain={chain_id}: "
                f"Alchemy"
            )

            return [
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
            if _normalize_address(tx.get("from")) == address
        ]

        print(
            f"[tracer] Internal transactions chain={chain_id}: "
            f"Etherscan raw={len(raw)} outgoing={len(outgoing)}"
        )

        if outgoing:
            return [
                _normalize_etherscan_internal(tx, chain_id)
                for tx in outgoing[:limit]
            ]

    if chain_id not in {56, 10}:
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
                    tx.get("category") == "internal"
                    and _normalize_address(tx.get("from")) == address
                )
            ]

            if internal:
                print(
                    f"[tracer] Internal transactions chain={chain_id}: "
                    f"Alchemy"
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
        block = _quicknode_block_number(chain_id)
        if block is not None:
            print(
                f"[tracer] QuickNode available for lower-level tracing "
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
                and _normalize_address(tx.get("to")) == address
            )
        ]

        if incoming:
            timestamps = [
                _safe_int(tx.get("timeStamp"))
                for tx in incoming
            ]
            timestamps = [x for x in timestamps if x]
            return min(timestamps) if timestamps else None

    alchemy_categories = (
        ["external", "erc20"]
        if chain_id in {56, 10}
        else ["external", "internal", "erc20"]
    )

    raw = _alchemy_fetch_transfers(
        address,
        chain_id,
        limit,
        direction="incoming",
        categories=alchemy_categories,
    )

    if raw is not None:
        incoming = [
            tx
            for tx in raw
            if _normalize_address(tx.get("to")) == address
        ]

        if incoming:
            timestamps = [
                _extract_alchemy_timestamp(tx)
                for tx in incoming
            ]
            timestamps = [x for x in timestamps if x]
            return min(timestamps) if timestamps else None

    raw = _goldrush_fetch_transactions(
        address,
        chain_id,
        limit,
    )

    if raw is not None:
        incoming = [
            tx
            for tx in raw
            if _normalize_address(tx.get("to_address")) == address
        ]

        if incoming:
            timestamps = [
                _parse_timestamp(tx.get("block_signed_at"))
                for tx in incoming
            ]
            timestamps = [x for x in timestamps if x]
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

    return (
        eth
        + tokens
        + internal
    )


def trace_wallet(
    start_address,
    api_key=None,
    chain_id=1,
    max_hops=3,
    limit_per_type=5,
):
    start_address = (
        start_address.lower()
    )

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
                first_in = (
                    get_incoming_transactions(
                        addr,
                        api_key,
                        chain_id,
                    )
                )

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

            for tx in txns:
                tx["hop"] = hop

                all_edges.append(tx)

                if (
                    tx["type"]
                    in HOPPABLE_TYPES
                    and tx["to"]
                    and tx["to"] != addr
                ):
                    next_layer.append(
                        tx["to"].lower()
                    )

        current_layer = list(
            dict.fromkeys(
                next_layer
            )
        )

        if not current_layer:
            break

    return (
        all_edges,
        incoming_timestamps,
    )


def _chain_id_from_activity(item):
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

        findings[chain_name] = cid

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

        providers = (
            _provider_order(cid)
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