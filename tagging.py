"""
static known-address dataset for tagging traced wallets against
known exchanges (VASPs) and bridge contracts

"""

KNOWN_VASPS = {
    # "0xexampleaddresslowercasehere": "Binance 14",
}

KNOWN_BRIDGES = {
    # "0xexamplebridgecontractaddress": "Wormhole Bridge (Ethereum)",
}


def tag_address(address):
    addr = address.lower()
    if addr in KNOWN_VASPS:
        return {"type": "exchange", "label": KNOWN_VASPS[addr]}
    if addr in KNOWN_BRIDGES:
        return {"type": "bridge", "label": KNOWN_BRIDGES[addr]}
    return None


def tag_all(addresses):
    return {addr: tag_address(addr) for addr in addresses}