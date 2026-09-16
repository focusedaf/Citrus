KNOWN_VASPS = {
    # Binance
    "0x28c6c06298d514db089934071355e5743bf21d60":
        "Binance 14",

    # Coinbase
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43":
        "Coinbase 10",

    # Kraken
    "0xda9dfa130df4de4673b89022ee50ff26f6ea73cf":
        "Kraken 13",

    # OKX
    "0x68841a1806ff291314946eebd0cda8b348e73d6d":
        "OKX 26",

    # OKX deposit address
    "0xae5dde433888a7456c3e0aecbb2e0a5748cbC1eb".lower():
        "OKX Deposit",
    
}

KNOWN_BRIDGES = {
    # Wormhole Core Contract — Ethereum
    "0x98f3c9e6e3face36baad05fe09d375ef1464288b":
        "Wormhole Core",

    # Wormhole Token Bridge — Ethereum
    "0x3ee18b2214aff97000d974cf647e7c347e8fa585":
        "Wormhole Token Bridge",

    # Stargate Native Pool — Ethereum
    "0x77b2043768d28e9c9ab44e1abfc95944bce57931":
        "Stargate Native Pool",

    # Stargate USDC Pool — Ethereum
    "0xc026395860db2d07ee33e05fe50ed7bd583189c7":
        "Stargate USDC Pool",

    # Stargate USDT Pool — Ethereum
    "0x933597a323eb81cae705c5bc29985172fd5a3973":
        "Stargate USDT Pool",
}


KNOWN_MIXERS = {}
 
 
def tag_address(address):
    addr = address.lower()
    if addr in KNOWN_VASPS:
        return {"type": "exchange", "label": KNOWN_VASPS[addr]}
    if addr in KNOWN_BRIDGES:
        return {"type": "bridge", "label": KNOWN_BRIDGES[addr]}
    if addr in KNOWN_MIXERS:
        return {"type": "mixer", "label": KNOWN_MIXERS[addr]}
    return None
 
 
def tag_all(addresses):
    return {addr: tag_address(addr) for addr in addresses}