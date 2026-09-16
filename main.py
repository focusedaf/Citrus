import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from tracer import trace_wallet
from graph_utils import build_graph, render_graph
from tagging import tag_all
from risk_engine import compute_risk

load_dotenv()
API_KEY = os.getenv("ETHERSCAN_KEY")

app = FastAPI(title="Crypto Fraud Attribution API")


@app.get("/")
def root():
    return {"message": "Crypto Fraud Attribution System - API is running"}


@app.post("/trace")
def trace(address: str, chain_id: int = 1, max_hops: int = 3):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="ETHERSCAN_KEY not set in .env")

    edges = trace_wallet(address, API_KEY, chain_id=chain_id, max_hops=max_hops)

    if not edges:
        return {
            "address": address,
            "message": "No outgoing transactions found (or address is inactive).",
            "edges": [],
            "tags": {},
            "risk": {"score": 0, "level": "Low", "reasons": []},
        }

    G = build_graph(edges)
    tags = tag_all(G.nodes)
    risk = compute_risk(edges, tags)
    
    render_graph(G, tags=tags, output_file="graph.html")

    return {
        "address": address,
        "edges": [
            {"from": src, "to": dst, "value_eth": float(val) / 1e18, "tx_hash": tx_hash}
            for src, dst, val, tx_hash in edges
        ],
        "tags": tags,
        "risk": risk,
    }


@app.post("/ingest-complaint")
def ingest_complaint(address: str):
    """
    Mock endpoint simulating ingestion from NCRP/SAHYOG complaint systems.
    In production this would be a webhook triggered by the complaint portal
    instead of a manually-called endpoint.
    """
    print(f"[MOCK] Complaint received for wallet: {address}")
    return trace(address)