from starlette.middleware.base import BaseHTTPMiddleware
import os
import glob
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
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
from evidence import save_evidence, verify_evidence, compute_hash
from storage import upload_evidence, upload_graph, upload_report, get_blob
from alert_engine import raise_alert
from dashboard import generate_dashboard_html, get_trace_detail
from config import DEFAULT_CHAIN_ID, GRAPHS_DIR, EVIDENCE_DIR
from workspace_service import (
    MEMBERS, ensure_workspace, get_workspace, list_workspaces, update_status,
    add_comment, add_task, toggle_task, invite_member, acknowledge_alert,
    toggle_node_flag, add_node_note, VALID_STATUSES,
)

load_dotenv()
API_KEY = os.getenv("ETHERSCAN_KEY")
app = FastAPI(
    title="CITRUS",
    version="1.1.0",
    description="Real-time crypto fraud attribution and investigation workspace API.",
    root_path="/api",
)

class StripAPIPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.scope["path"] == "/api":
            request.scope["path"] = "/"
        elif request.scope["path"].startswith("/api/"):
            request.scope["path"] = request.scope["path"][4:]

        return await call_next(request)


app.add_middleware(StripAPIPrefixMiddleware)

# Frontend runs separately during development/deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    actor: str = "m1"

class StatusIn(BaseModel):
    status: str
    actor: str = "m1"

class TaskIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    assignee: str = "m1"
    actor: str = "m1"

class InviteIn(BaseModel):
    member_id: str
    actor: str = "m1"

class NodeNoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    actor: str = "m1"

class TraceOptions(BaseModel):
    address: str
    chain_id: int = DEFAULT_CHAIN_ID
    max_hops: int = 3
    check_cross_chain: bool = True


@app.on_event("startup")
def on_startup():
    try:
        init_db()
        # os.makedirs(GRAPHS_DIR, exist_ok=True)
        # os.makedirs(EVIDENCE_DIR, exist_ok=True)
        print("[DB] Database initialized successfully.")
    except Exception as exc:
        print(f"[DB] Database initialization failed: {exc}")
        raise

def _edge_amount(e):
    if e["token"] == "ETH":
        return float(e["value"]) / 1e18

    decimals = e.get("value_decimals", 18)

    return float(e["value"]) / (10 ** decimals)


def _graph_path_for(trace_id):
    return os.path.join(GRAPHS_DIR, f"graph_{trace_id}.html")


@app.get("/")
def root():
    return {
        "message": "CITRUS",
        "database": "Neon PostgreSQL",
        "endpoints": {
            "dashboard": "/dashboard",
            "graph": "/graph/{trace_id}",
            "traces": "/traces",
            "alerts": "/alerts",
            "evidence": "/evidence/{trace_id}",
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

    
    address = address.lower()

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
            tags={},
        )

        report_path = generate_pdf_report(
            empty_summary,
            empty_risk,
            trace_id=trace_id,
        )

        return {
            "trace_id": trace_id,
            "workspace_id": ensure_workspace(trace_id, address, chain="Ethereum"),
            "address": address,
            "message": "No transactions found (or address is inactive).",
            "edges": [],
            "tags": {},
            "investigation_table": [],
            "summary": empty_summary,
            "risk": empty_risk,
            "report_path": report_path,
            "report_url": f"/report/{trace_id}",
            "graph_url": None,
            "evidence_url": None,
            "alert_raised": None,
        }

    G = build_graph(edges)
    tags = tag_all(G.nodes, edges=edges, api_key=API_KEY, chain_id=chain_id)
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
                "function_name": e.get("function_name"),
            }
        )

    
    raw_records = [e["_raw"] for e in edges if e.get("_raw")]
    evidence_core = {
        "address": address,
        "raw_records": raw_records,
        "derived_edges": serialized_edges,
    }
    evidence_hash = compute_hash(evidence_core)

    trace_id = save_trace(
        address,
        chain_id,
        summary,
        serialized_edges,
        risk,
        evidence_hash=evidence_hash,
        tags=tags,
    )

    print(f"[DB] Trace saved successfully. trace_id={trace_id}")

    print("[DEBUG] Starting evidence Blob upload")

    evidence_path, _ = save_evidence(
        trace_id,
        address,
        raw_records,
        serialized_edges,
        precomputed_hash=evidence_hash,
    )

    print(f"[EVIDENCE] Bundle saved: {evidence_path}")

    evidence_blob_url = upload_evidence(
    trace_id,
    {
        "address": address,
        "raw_records": raw_records,
        "derived_edges": serialized_edges,
        "evidence_hash": evidence_hash,
    },
    )

    print(f"[EVIDENCE] Uploaded to Blob: {evidence_blob_url}")

    print(f"[DEBUG] Evidence Blob upload successful: {evidence_blob_url}")

    print("[DEBUG] Starting graph Blob upload")

    graph_path = render_graph(
        G,
        tags=tags,
        start_address=address,
        output_file=_graph_path_for(trace_id),
    )

    graph_blob_url = upload_graph(
    trace_id,
    graph_path,
    )

    print(f"[GRAPH] Uploaded to Blob: {graph_blob_url}")

    print(f"[DEBUG] Graph Blob upload successful: {graph_blob_url}")

    print("[DEBUG] Starting report Blob upload")

    report_path = generate_pdf_report(
        summary,
        risk,
        trace_id=trace_id,
        evidence={"hash": evidence_hash, "path": evidence_path},
    )

    print(f"[REPORT] PDF generated: {report_path}")

    print(f"[DEBUG] Report Blob upload successful: {report_blob_url}")

    report_blob_url = upload_report(
    trace_id,
    report_path,
    )

    print(f"[REPORT] Uploaded to Blob: {report_blob_url}")

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

    workspace_id = ensure_workspace(
        trace_id,
        address,
        chain="Ethereum",
        complaint_id=f"NCRP/2026/LIVE/{trace_id:06d}",
    )

    return {
        "trace_id": trace_id,
        "workspace_id": workspace_id,
        "address": address,

        "edges": serialized_edges,

        "tags": tags,

        "investigation_table": table,

        "summary": summary,

        "risk": risk,

        "report_path": report_path,

        "report_url": f"/report/{trace_id}",
        "graph_url": f"/graph/{trace_id}",
        "evidence_url": f"/evidence/{trace_id}",

        "blob_artifacts": {
        "report": report_blob_url,
        "graph": graph_blob_url,
        "evidence": evidence_blob_url,
        },

        "alert_raised": alert_message,
    }


@app.post("/ingest-complaint")
def ingest_complaint(address: str):
    address = address.lower()
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



@app.get("/members")
def members():
    return MEMBERS


@app.get("/workspaces")
def workspaces(limit: int = 100):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return list_workspaces(limit)


@app.get("/workspaces/{workspace_id}")
def workspace(workspace_id: str):
    result = get_workspace(workspace_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return result


@app.patch("/workspaces/{workspace_id}/status")
def workspace_status(workspace_id: str, payload: StatusIn):
    try:
        ok = update_status(workspace_id, payload.status, payload.actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return get_workspace(workspace_id)


@app.post("/workspaces/{workspace_id}/comments")
def workspace_comment(workspace_id: str, payload: CommentIn):
    if not get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"id": add_comment(workspace_id, payload.text.strip(), payload.actor), **get_workspace(workspace_id)}


@app.post("/workspaces/{workspace_id}/tasks")
def workspace_task(workspace_id: str, payload: TaskIn):
    if not get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    task_id = add_task(workspace_id, payload.text.strip(), payload.assignee, payload.actor)
    return {"task_id": task_id, **get_workspace(workspace_id)}


@app.patch("/workspaces/{workspace_id}/tasks/{task_id}")
def workspace_task_toggle(workspace_id: str, task_id: str, actor: str = "m1"):
    result = toggle_task(workspace_id, task_id, actor)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return get_workspace(workspace_id)


@app.post("/workspaces/{workspace_id}/members")
def workspace_invite(workspace_id: str, payload: InviteIn):
    if not get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        invite_member(workspace_id, payload.member_id, payload.actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return get_workspace(workspace_id)


@app.patch("/alerts/{alert_id}/ack")
def alert_ack(alert_id: str):
    if not acknowledge_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True, "alert_id": alert_id}


@app.post("/workspaces/{workspace_id}/nodes/{address}/flag")
def node_flag(workspace_id: str, address: str, actor: str = "m1"):
    if not get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    flagged = toggle_node_flag(workspace_id, address.lower(), actor)
    return {"flagged": flagged, "workspace": get_workspace(workspace_id)}


@app.post("/workspaces/{workspace_id}/nodes/{address}/notes")
def node_note(workspace_id: str, address: str, payload: NodeNoteIn):
    if not get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    add_node_note(workspace_id, address.lower(), payload.text.strip(), payload.actor)
    return get_workspace(workspace_id)


@app.post("/workspaces/{workspace_id}/report")
def workspace_report(workspace_id: str):
    ws = get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    trace_id = ws["traceId"]
    # /report/{trace_id} is the canonical PDF generator/download endpoint.
    return {"trace_id": trace_id, "report_url": f"/report/{trace_id}"}


@app.get("/dashboard/stats")
def dashboard_stats(days: int = 30):
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")
    traces = get_all_traces(500)
    alerts = get_all_alerts(500)
    active = [t for t in traces if t.get("risk_level") and t.get("risk_level") != "Low"]
    vasp_hits = {}
    entity_counts = {"vasp": 0, "mixer": 0, "bridge": 0, "contract": 0, "unknown": 0}
    for t in traces:
        tags = t.get("tags_json") or {}
        for tag in tags.values():
            typ = (tag or {}).get("entity_type", "unknown")
            entity_counts[typ] = entity_counts.get(typ, 0) + 1
            if typ == "vasp":
                label = (tag or {}).get("label", "Unknown VASP")
                vasp_hits[label] = vasp_hits.get(label, 0) + 1
    return {
        "active_cases": len(active),
        "total_workspaces": len(traces),
        "critical_cases": sum(1 for t in traces if t.get("risk_level") == "Critical"),
        "funds_traced_inr": 0,
        "vasps_identified": len(vasp_hits),
        "open_alerts": sum(1 for a in alerts if not a.get("acknowledged", False)),
        "entity_counts": entity_counts,
        "top_exchanges": sorted(({"name": k, "hits": v} for k, v in vasp_hits.items()), key=lambda x: x["hits"], reverse=True)[:6],
    }


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


@app.get("/graph/{trace_id}", response_class=HTMLResponse)
async def graph_for_trace(trace_id: int):
    blob_path = f"citrus/graphs/graph_{trace_id}.html"

    result = await get_blob(blob_path)

    if result is None or result.status_code != 200:
        raise HTTPException(
            status_code=404,
            detail=f"No graph stored for trace {trace_id}.",
        )

    return HTMLResponse(
        content=result.content.decode("utf-8"),
        status_code=200,
    )

@app.get(
    "/graph",
    response_class=HTMLResponse,
)
def graph_latest():
    """Backward-compatible alias: serves the most recently generated graph."""
    candidates = glob.glob(os.path.join(GRAPHS_DIR, "graph_*.html"))

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="No graph has been generated yet. Run /trace first.",
        )

    latest = max(candidates, key=os.path.getmtime)

    try:
        with open(latest, "r", encoding="utf-8") as f:
            html = f.read()
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read graph: {exc}",
        )

    return HTMLResponse(content=html, status_code=200)

@app.get("/evidence/{trace_id}")
async def get_evidence(trace_id: int):
    blob_path = f"citrus/evidence/evidence_{trace_id}.json"

    result = await get_blob(blob_path)

    if result is None or result.status_code != 200:
        raise HTTPException(
            status_code=404,
            detail=f"No evidence bundle found for trace {trace_id}.",
        )

    return Response(
        content=result.content,
        media_type=result.content_type or "application/json",
        headers={
            "Content-Disposition": f'inline; filename="evidence_{trace_id}.json"'
        },
    )


@app.get("/evidence/{trace_id}/verify")
def verify_evidence_endpoint(trace_id: int):
    result = verify_evidence(trace_id)

    if not result["exists"]:
        raise HTTPException(
            status_code=404,
            detail=f"No evidence bundle found for trace {trace_id}.",
        )

    return result


@app.get("/traces")
def list_traces(limit: int = 50):

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 500",
        )

    return get_all_traces(limit)


@app.get("/reports")
def list_reports(limit: int = 100):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    rows = get_all_traces(limit)
    reports = []
    for row in rows:
        reports.append({
            "id": f"r-{row['id']}",
            "name": f"Investigation report – trace {row['id']}.pdf",
            "at": row["created_at"],
            "by": "m1",
            "kind": "PDF",
            "workspaceId": f"CT-{1000 + row['id']}",
            "traceId": row["id"],
            "reportUrl": f"/report/{row['id']}",
            "evidenceUrl": f"/evidence/{row['id']}",
        })
    return reports


@app.get("/alerts")
def list_alerts(limit: int = 50):

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 500",
        )

    return get_all_alerts(limit)

@app.get("/report/{trace_id}")
async def view_report(trace_id: int):
    blob_path = f"citrus/reports/report_{trace_id}.pdf"

    result = await get_blob(blob_path)

    if result is None or result.status_code != 200:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for trace {trace_id}.",
        )

    return Response(
        content=result.content,
        media_type=result.content_type or "application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="report_{trace_id}.pdf"'
        },
    )