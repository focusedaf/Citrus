# Real-Time Crypto Fraud Attribution System

**SIH 2026 — PS 183: Real-Time Identification of Fraud-Linked Cryptocurrency Exchanges from Victim-Reported Wallet Addresses through Automated Blockchain Analytics**

Team: Sentinals

## Problem

Cyber fraud victims report suspect cryptocurrency wallet addresses used by scammers, but manually tracing where those funds end up (which exchange, which VASP) is slow and requires technical expertise that inludes delaying asset freezing and evidence collection.

## Solution

This system automatically traces a victim-reported wallet address across multiple blockchain hops, builds a transaction graph, tags addresses against known exchanges/VASPs, and generates a rule-based risk score which turns a manual multi-hour investigation into a near-instant lookup.

## Features

- **Automated multi-hop tracing** — follows outgoing transactions from a wallet address via the Etherscan API
- **Transaction graph visualization** — interactive graph built with NetworkX + pyvis
- **VASP/exchange tagging** — matches traced addresses against a known-address dataset
- **Rule-based risk scoring** — flags wallets by hop count, exchange type, and cross-chain movement
- **Mock complaint ingestion endpoint** — simulates NCRP/SAHYOG integration


## Project Structure

```
Citrus/
├── main.py              # FastAPI app + endpoints
├── tracer.py            # BFS hop-following logic
├── graph_utils.py        # NetworkX graph building + pyvis rendering
├── tagging.py            # Known-address dictionary + tagging logic
├── risk_engine.py        # Rule-based risk scoring
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup

1. Clone the repo
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd Citrus
   ```

2. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Add your Etherscan API key
   ```bash
   cp .env.example .env
   # then edit .env and paste your key
   ```

5. Run the server
   ```bash
   uvicorn main:app --reload
   ```

6. Trace a wallet
   ```bash
   curl -X POST "http://127.0.0.1:8000/trace?address=0xYOUR_ADDRESS"
   ```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/trace` | POST | Traces a wallet address, returns graph edges, tags, and risk score |
| `/ingest-complaint` | POST | Mock endpoint simulating NCRP/SAHYOG complaint ingestion |

## Limitations (Current Prototype)

- Single-chain (Ethereum) tracing only — multi-chain (BSC, Solana) planned
- Known-address list is a small manually curated seed set, not a full labeled dataset
- Address clustering uses direct matching, not multi-input/common-spend heuristics
- Risk scoring is rule-based (v1); GNN-based scoring is the planned upgrade
- Mixer/tumbler detection not yet implemented
- NCRP/SAHYOG integration is mocked, not live



