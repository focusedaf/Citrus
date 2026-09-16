KNOWN_VASPS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": ("exchange", "Binance 14"),
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43": ("exchange", "Coinbase 10"),
    "0xda9dfa130df4de4673b89022ee50ff26f6ea73cf": ("exchange", "Kraken 13"),
    "0x68841a1806ff291314946eebd0cda8b348e73d6d": ("exchange", "OKX 26"),
    "0xae5dde433888a7456c3e0aecbb2e0a5748cbc1eb": ("exchange", "OKX Deposit"),
}

KNOWN_BRIDGES = {
    "0x98f3c9e6e3face36baad05fe09d375ef1464288b": ("cross_chain_bridge", "Wormhole Core"),
    "0x3ee18b2214aff97000d974cf647e7c347e8fa585": ("cross_chain_bridge", "Wormhole Token Bridge"),
    "0x77b2043768d28e9c9ab44e1abfc95944bce57931": ("liquidity_bridge", "Stargate Native Pool"),
    "0xc026395860db2d07ee33e05fe50ed7bd583189c7": ("liquidity_bridge", "Stargate USDC Pool"),
    "0x933597a323eb81cae705c5bc29985172fd5a3973": ("liquidity_bridge", "Stargate USDT Pool"),
}

# Real, verified Tornado Cash ETH pool contract addresses (Ethereum mainnet).
KNOWN_MIXERS = {
    "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc": ("tumbler", "Tornado Cash: 0.1 ETH"),
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": ("tumbler", "Tornado Cash: 1 ETH"),
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": ("tumbler", "Tornado Cash: 10 ETH"),
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": ("tumbler", "Tornado Cash: 100 ETH"),
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": ("tumbler", "Tornado Cash: Router"),
}

# Infrastructure contracts - NOT wallets and NOT VASPs.
KNOWN_CONTRACTS = {
    "0xdac17f958d2ee523a2206206994597c13d831ec7": ("token_contract", "USDT Token Contract"),
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": ("token_contract", "USDC Token Contract"),
    "0x6b175474e89094c44da98b954eedeac495271d0f": ("token_contract", "DAI Token Contract"),
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": ("token_contract", "WETH Token Contract"),
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": ("dex_router", "Uniswap V2 Router"),
}


def tag_address(address):
    addr = address.lower()
    if addr in KNOWN_VASPS:
        subtype, label = KNOWN_VASPS[addr]
        return {"entity_type": "vasp", "entity_subtype": subtype, "label": label}
    if addr in KNOWN_BRIDGES:
        subtype, label = KNOWN_BRIDGES[addr]
        return {"entity_type": "bridge", "entity_subtype": subtype, "label": label}
    if addr in KNOWN_MIXERS:
        subtype, label = KNOWN_MIXERS[addr]
        return {"entity_type": "mixer", "entity_subtype": subtype, "label": label}
    if addr in KNOWN_CONTRACTS:
        subtype, label = KNOWN_CONTRACTS[addr]
        return {"entity_type": "contract", "entity_subtype": subtype, "label": label}
    return None


def tag_all(addresses):
    return {addr: tag_address(addr) for addr in addresses}