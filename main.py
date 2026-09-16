import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from tracer import trace_wallet, cross_chain_reuse_check
from graph_utils import (
    build_graph,
    render_graph,
    investigation_table,
    investigation_summary,
)
from tagging import tag_all
from risk_engine import compute_risk
from db import (
    init_db,
    save_trace,
    save_complaint,
    save_alert,
    get_all_traces,
    get_all_alerts,
    get_trace_by_id,
)
from report_generator import generate_pdf_report
from alert_engine import raise_alert
from dashboard import generate_dashboard_html, get_trace_detail
from config import DEFAULT_CHAIN_ID

load_dotenv()
API_KEY = os.getenv("ETHERSCAN_KEY")
app = FastAPI(
    title="CITRUS",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    try:
        init_db()
        print("[DB] Database initialized successfully.")
    except Exception as exc:
        print(f"[DB] Database initialization failed: {exc}")
        raise

def _edge_amount(e):
    if e["token"] == "ETH":
        return float(e["value"]) / 1e18

    decimals = e.get("value_decimals", 18)

    return float(e["value"]) / (10 ** decimals)


@app.get("/")
def root():
    return {
        "message": "CITRUS",
        "database": "Neon PostgreSQL",
        "endpoints": {
            "dashboard": "/dashboard",
            "graph": "/graph",
            "traces": "/traces",
            "alerts": "/alerts",
            "docs": "/docs",
        },
    }

@app.post("/trace")
def trace(
    address: str,
    chain_id: int = DEFAULT_CHAIN_ID,
    max_hops: int = 3,
    check_cross_chain: bool = True,
):
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ETHERSCAN_KEY not set in .env",
        )

    edges, incoming_timestamps = trace_wallet(
        address,
        API_KEY,
        chain_id=chain_id,
        max_hops=max_hops,
    )

    if not edges:

        empty_risk = compute_risk(
            [],
            {},
            address,
        )

        empty_summary = {
            "reported_address": address,
            "chain": "Ethereum",
            "assets_observed": [],
            "transactions_analyzed": 0,
            "unique_counterparties": 0,
            "max_trace_depth": 0,
            "entity_findings": {
                "vasp": "None detected",
                "bridge": "None detected",
                "mixer": "None detected",
                "known_contracts": "None detected",
                "unidentified_wallets": 0,
            },
            "spoofed_tokens_detected": "None detected",
            "cross_chain_activity": "None detected",
            "risk_indicators": [],
            "risk_level": "Low",
            "risk_score": 0,
        }

        trace_id = save_trace(
            address,
            chain_id,
            empty_summary,
            [],
            empty_risk,
        )

        report_path = generate_pdf_report(
            empty_summary,
            empty_risk,
            trace_id=trace_id,
        )

        return {
            "trace_id": trace_id,
            "address": address,
            "message": "No outgoing transactions found (or address is inactive).",
            "edges": [],
            "tags": {},
            "investigation_table": [],
            "summary": empty_summary,
            "risk": empty_risk,
            "report_path": report_path,
            "report_url": f"/report/{trace_id}",
            "graph_url": None,
            "alert_raised": None,
        }

    G = build_graph(edges)
    tags = tag_all(G.nodes)
    cross_chain_findings = {}

    if check_cross_chain:
        cross_chain_findings = cross_chain_reuse_check(
            address,
            API_KEY,
            primary_chain_id=chain_id,
        )

    risk = compute_risk(
        edges,
        tags,
        address,
        incoming_timestamps,
        cross_chain_findings,
    )

    table = investigation_table(
        G,
        tags,
    )

    summary = investigation_summary(
        G,
        tags,
        edges,
        address,
        risk,
        cross_chain_findings,
    )

    graph_path = render_graph(
        G,
        tags=tags,
        start_address=address,
        output_file="graph.html",
    )

    serialized_edges = []

    for e in edges:

        serialized_edges.append(
            {
                "from": e["from"],
                "to": e["to"],
                "type": e["type"],
                "token": e["token"],
                "amount": _edge_amount(e),
                "hop": e["hop"],
                "timestamp": e["timestamp"],
                "tx_hash": e["tx_hash"],
                "is_spoofed_token": e.get(
                    "is_spoofed_token",
                    False,
                ),
            }
        )

    trace_id = save_trace(
        address,
        chain_id,
        summary,
        serialized_edges,
        risk,
    )

    print(f"[DB] Trace saved successfully. trace_id={trace_id}")

    report_path = generate_pdf_report(
        summary,
        risk,
        trace_id=trace_id,
    )

    print(f"[REPORT] PDF generated: {report_path}")

    alert_message = raise_alert(
        address,
        risk,
        trace_id=trace_id,
    )

    if alert_message:

        save_alert(
            trace_id,
            address,
            risk["level"],
            alert_message,
        )

        print(
            f"[DB] Alert saved successfully for trace_id={trace_id}"
        )

    return {
        "trace_id": trace_id,
        "address": address,

        "edges": serialized_edges,

        "tags": tags,

        "investigation_table": table,

        "summary": summary,

        "risk": risk,

        "report_path": report_path,

        "report_url": f"/report/{trace_id}",
        "graph_url": "/graph",

        "alert_raised": alert_message,
    }


@app.post("/ingest-complaint")
def ingest_complaint(address: str):
    print(
        f"[MOCK] Complaint received for wallet: {address}"
    )

    result = trace(address)

    save_complaint(
        address,
        source="NCRP/SAHYOG (mock)",
        trace_id=result.get("trace_id"),
    )

    return result


@app.get(
    "/dashboard",
    response_class=HTMLResponse,
)
def dashboard():
    html = generate_dashboard_html()

    return HTMLResponse(
        content=html,
        status_code=200,
    )


@app.get(
    "/dashboard/trace/{trace_id}",
    response_class=HTMLResponse,
)
def dashboard_trace(trace_id: int):
    html = get_trace_detail(trace_id)

    return HTMLResponse(
        content=html,
        status_code=200,
    )


@app.get(
    "/graph",
    response_class=HTMLResponse,
)
def graph():
    graph_path = "graph.html"

    if not os.path.exists(graph_path):
        raise HTTPException(
            status_code=404,
            detail="No graph has been generated yet. Run /trace first.",
        )

    try:
        with open(
            graph_path,
            "r",
            encoding="utf-8",
        ) as f:
            html = f.read()

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read graph: {exc}",
        )

    return HTMLResponse(
        content=html,
        status_code=200,
    )


@app.get("/traces")
def list_traces(limit: int = 50):

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 500",
        )

    return get_all_traces(limit)


@app.get("/alerts")
def list_alerts(limit: int = 50):

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 500",
        )

    return get_all_alerts(limit)


@app.get("/report/{trace_id}")
def view_report(trace_id: int):

    trace_row = get_trace_by_id(
        trace_id
    )

    if not trace_row:
        raise HTTPException(
            status_code=404,
            detail="Trace not found",
        )

    summary = trace_row["summary_json"]

    if not summary:
        raise HTTPException(
            status_code=500,
            detail="Trace exists but contains no report summary.",
        )

    risk = {
        "score": trace_row["risk_score"],
        "level": trace_row["risk_level"],
        "label": "Rule-Based Risk Indicator (Prototype)",
        "reasons": summary.get(
            "risk_indicators",
            [],
        ),
    }

    path = generate_pdf_report(
        summary,
        risk,
        trace_id=trace_id,
    )

    if not os.path.exists(path):
        raise HTTPException(
            status_code=500,
            detail="PDF report could not be generated.",
        )

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=os.path.basename(path),
        headers={
            "Content-Disposition": (
                f'inline; filename="{os.path.basename(path)}"'
            )
        },
    )