from starlette.middleware.base import BaseHTTPMiddleware
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse, Response
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
from evidence import compute_hash
from storage import upload_evidence, upload_graph, upload_report, get_blob
from alert_engine import raise_alert
from config import DEFAULT_CHAIN_ID, SUPPORTED_CHAINS
from workspace_service import (
    MEMBERS,
    ensure_workspace,
    get_workspace,
    list_workspaces,
    update_status,
    add_comment,
    add_task,
    toggle_task,
    invite_member,
    acknowledge_alert,
    toggle_node_flag,
    add_node_note,
    VALID_STATUSES,
)

load_dotenv()

API_KEY = os.getenv("ETHERSCAN_KEY")


app = FastAPI(
    title="CITRUS",
    version="1.1.0",
    description="Real-time crypto fraud attribution and investigation workspace API.",
    root_path="/api",
)


class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api"):
            request.scope["path"] = request.url.path[4:] or "/"
        return await call_next(request)


app.add_middleware(StripApiPrefixMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://citrus-seven-livid.vercel.app",
        "http://localhost:3000",
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
def startup():
    init_db()


def _edge_amount(edge):
    if edge.get("token") == "ETH":
        return float(edge.get("value", 0)) / 1e18

    decimals = edge.get("value_decimals", 18)

    try:
        return float(edge.get("value", 0)) / (10 ** decimals)
    except (TypeError, ValueError):
        return 0.0


def _chain_name(chain_id: int) -> str:
    return SUPPORTED_CHAINS.get(chain_id, f"Chain {chain_id}")


@app.get("/")
def root():
    return {
        "name": "CITRUS",
        "version": "1.1.0",
        "status": "running",
        "database": "Neon PostgreSQL",
        "endpoints": {
            "trace": "/api/trace",
            "complaint": "/api/ingest-complaint",
            "dashboard": "/api/dashboard",
            "traces": "/api/traces",
            "alerts": "/api/alerts",
            "graph": "/api/graph/{trace_id}",
            "report": "/api/report/{trace_id}",
            "evidence": "/api/evidence/{trace_id}",
            "evidence_verify": "/api/evidence/{trace_id}/verify",
            "workspaces": "/api/workspaces",
        },
    }


@app.post("/trace")
def trace(
    address: str,
    chain_id: int = DEFAULT_CHAIN_ID,
    max_hops: int = 3,
    check_cross_chain: bool = True,
):
    try:
        address = address.lower().strip()

        if not address:
            raise HTTPException(
                status_code=400,
                detail="Wallet address is required.",
            )

        if chain_id not in SUPPORTED_CHAINS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported chain_id: {chain_id}",
            )

        if max_hops < 1 or max_hops > 10:
            raise HTTPException(
                status_code=400,
                detail="max_hops must be between 1 and 10.",
            )

        if not any(
            [
                os.getenv("ETHERSCAN_KEY"),
                os.getenv("ALCHEMY_API_KEY"),
                os.getenv("GOLDRUSH_API_KEY"),
                os.getenv("QUICKNODE_BSC_URL"),
            ]
        ):
            raise HTTPException(
                status_code=500,
                detail="No blockchain data provider is configured.",
            )

        edges, incoming_timestamps = trace_wallet(
            address,
            API_KEY,
            chain_id=chain_id,
            max_hops=max_hops,
        )

        if not edges:
            risk = {
                "score": 0,
                "level": "Low",
                "reasons": ["No outgoing transactions found."],
            }

            trace_id = save_trace(
                    address=address,
                    chain_id=chain_id,
                    summary={
                        "chain": _chain_name(chain_id),
                        "address": address,
                        "nodes": 1,
                        "edges": 0,
                    },
                    edges=[],
                    risk=risk,
                    tags={},
                    evidence_hash=None,
                    max_hops=max_hops,
                    )

            workspace_id = ensure_workspace(
                trace_id=trace_id,
                address=address,
                chain_id=chain_id,
                risk=risk,
            )

            return {
                "trace_id": trace_id,
                "workspace_id": workspace_id,
                "address": address,
                "chain_id": chain_id,
                "chain": _chain_name(chain_id),
                "edges": [],
                "tags": [],
                "table": [],
                "summary": {
                    "chain": _chain_name(chain_id),
                    "address": address,
                    "nodes": 1,
                    "edges": 0,
                },
                "risk": risk,
                "cross_chain": [],
            }

        G = build_graph(edges)

        tags = tag_all(
            address,
            edges,
            chain_id=chain_id,
        )

        cross_chain = []

        if check_cross_chain:
            cross_chain = cross_chain_reuse_check(
                address
            )

        risk = compute_risk(
            address=address,
            edges=edges,
            tags=tags,
            incoming_timestamps=incoming_timestamps,
            cross_chain_results=cross_chain,
            max_hops=max_hops,
        )

        table = investigation_table(G)

        summary = investigation_summary(
            G,
            address=address,
            chain_id=chain_id,
            tags=tags,
            risk=risk,
            cross_chain=cross_chain,
        )

        serialized_edges = []

        for edge in edges:
            serialized = {
                key: value
                for key, value in edge.items()
                if key != "_raw"
            }

            serialized["amount"] = _edge_amount(edge)
            serialized_edges.append(serialized)

        raw_records = []

        for edge in edges:
            raw = edge.get("_raw")

            if raw is not None:
                raw_records.append(raw)

        evidence_core = {
            "address": address,
            "raw_records": raw_records,
            "derived_edges": serialized_edges,
        }

        evidence_hash = compute_hash(evidence_core)

        trace_id = save_trace(
        address=address,
        chain_id=chain_id,
        summary=summary,
        edges=serialized_edges,
        risk=risk,
        tags=tags,
        evidence_hash=evidence_hash,
        max_hops=max_hops,
        )

        evidence_blob_url = upload_evidence(
            trace_id,
            {
                **evidence_core,
                "sha256": evidence_hash,
            },
        )

        graph_html = render_graph(
        G,
        tags=tags,
        start_address=address,
        )

        graph_blob_url = upload_graph(
            trace_id,
            graph_html,
        )

        report_pdf = generate_pdf_report(
            summary=summary,
            risk=risk,
            trace_id=trace_id,
            evidence=evidence,
        )

        report_blob_url = upload_report(
            trace_id,
            report_pdf,
        )

        alert = raise_alert(
            address,
            risk,
            trace_id=trace_id,
        )

        if alert:
           save_alert(
            trace_id=trace_id,
            address=address,
            risk_level=risk["level"],
            message=alert,
        )

        workspace_id = ensure_workspace(
            trace_id=trace_id,
            address=address,
            chain_id=chain_id,
            risk=risk,
        )

        return {
            "trace_id": trace_id,
            "workspace_id": workspace_id,
            "address": address,
            "chain_id": chain_id,
            "chain": _chain_name(chain_id),
            "edges": serialized_edges,
            "tags": tags,
            "table": table,
            "summary": summary,
            "risk": risk,
            "cross_chain": cross_chain,
            "artifacts": {
                "evidence": evidence_blob_url,
                "graph": graph_blob_url,
                "report": report_blob_url,
            },
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        print("\n========== CITRUS TRACE CRASH ==========")
        print(f"address={address}")
        print(f"chain_id={chain_id}")
        print(f"max_hops={max_hops}")
        print(f"error={repr(exc)}")
        traceback.print_exc()
        print("========== END CITRUS TRACE CRASH ==========\n")
        raise

@app.post("/ingest-complaint")
def ingest_complaint(address: str):
    address = address.lower().strip()

    if not address:
        raise HTTPException(
            status_code=400,
            detail="Wallet address is required.",
        )

    print(f"[MOCK] Complaint received for wallet: {address}")

    result = trace(
        address=address,
        chain_id=DEFAULT_CHAIN_ID,
        max_hops=3,
        check_cross_chain=True,
    )

    save_complaint(
        address=address,
        source="NCRP/SAHYOG (mock)",
        trace_id=result.get("trace_id"),
    )

    return {
        "message": "Complaint ingested.",
        "source": "NCRP/SAHYOG (mock)",
        "trace": result,
    }


@app.get("/dashboard")
def dashboard():
    return {
        "traces": get_all_traces(),
        "alerts": get_all_alerts(),
    }


@app.get("/dashboard/stats")
def dashboard_stats(days: int = 30):
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=400,
            detail="days must be between 1 and 365.",
        )

    traces = get_all_traces()
    alerts = get_all_alerts()

    return {
        "days": days,
        "total_traces": len(traces),
        "total_alerts": len(alerts),
        "traces": traces,
        "alerts": alerts,
    }


@app.get("/traces")
def traces():
    return get_all_traces()


@app.get("/alerts")
def alerts():
    return get_all_alerts()


@app.get("/graph/{trace_id}")
async def get_graph(trace_id: int):
    blob_path = f"graphs/graph_{trace_id}.html"

    try:
        result = await get_blob(blob_path)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Graph not found: {exc}",
        )

    return HTMLResponse(
        content=result.content.decode("utf-8"),
        media_type="text/html",
    )


@app.get("/evidence/{trace_id}")
async def get_evidence(trace_id: int):
    blob_path = f"evidence/evidence_{trace_id}.json"

    try:
        result = await get_blob(blob_path)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence not found: {exc}",
        )

    return Response(
        content=result.content,
        media_type="application/json",
    )


@app.get("/evidence/{trace_id}/verify")
async def verify_evidence_endpoint(trace_id: int):
    blob_path = f"evidence/evidence_{trace_id}.json"

    try:
        result = await get_blob(blob_path)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence not found: {exc}",
        )

    try:
        bundle = json.loads(result.content.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid evidence JSON: {exc}",
        )

    stored_hash = bundle.get("sha256")

    core = {
        "address": bundle.get("address"),
        "raw_records": bundle.get("raw_records"),
        "derived_edges": bundle.get("derived_edges"),
    }

    recomputed_hash = compute_hash(core)

    return {
        "exists": True,
        "stored_hash": stored_hash,
        "recomputed_hash": recomputed_hash,
        "intact": stored_hash == recomputed_hash,
        "collected_at": bundle.get("collected_at"),
    }


@app.get("/report/{trace_id}")
async def get_report(trace_id: int):
    blob_path = f"reports/report_{trace_id}.pdf"

    try:
        result = await get_blob(blob_path)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Report not found: {exc}",
        )

    return Response(
        content=result.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=report_{trace_id}.pdf"
        },
    )


@app.get("/reports")
def reports():
    traces = get_all_traces()

    return [
        {
            "trace_id": trace.get("id"),
            "address": trace.get("address"),
            "chain_id": trace.get("chain_id"),
            "risk": {
                "score": trace.get("risk_score", 0),
                "level": trace.get("risk_level", "Low"),
            },
            "created_at": trace.get("created_at"),
        }
        for trace in traces
    ]


@app.get("/members")
def members():
    return MEMBERS


@app.get("/workspaces")
def workspaces():
    return list_workspaces()


@app.get("/workspaces/{workspace_id}")
def workspace(workspace_id: str):
    result = get_workspace(workspace_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    return result


@app.patch("/workspaces/{workspace_id}/status")
def workspace_status(
    workspace_id: str,
    payload: StatusIn,
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid statuses: {sorted(VALID_STATUSES)}",
        )

    result = update_status(
        workspace_id,
        payload.status,
        payload.actor,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    return result


@app.post("/workspaces/{workspace_id}/comments")
def workspace_comment(
    workspace_id: str,
    payload: CommentIn,
):
    result = add_comment(
        workspace_id,
        payload.text,
        payload.actor,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    return result


@app.post("/workspaces/{workspace_id}/tasks")
def workspace_task(
    workspace_id: str,
    payload: TaskIn,
):
    result = add_task(
        workspace_id,
        payload.text,
        payload.assignee,
        payload.actor,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    return result


@app.patch("/workspaces/{workspace_id}/tasks/{task_id}")
def workspace_task_toggle(
    workspace_id: str,
    task_id: str,
):
    result = toggle_task(
        workspace_id,
        task_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace or task not found.",
        )

    return result


@app.post("/workspaces/{workspace_id}/members")
def workspace_invite(
    workspace_id: str,
    payload: InviteIn,
):
    result = invite_member(
        workspace_id,
        payload.member_id,
        payload.actor,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    return result


@app.patch("/alerts/{alert_id}/ack")
def acknowledge_workspace_alert(
    alert_id: int,
):
    result = acknowledge_alert(alert_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Alert not found.",
        )

    return result


@app.post("/workspaces/{workspace_id}/nodes/{address}/flag")
def flag_workspace_node(
    workspace_id: str,
    address: str,
):
    result = toggle_node_flag(
        workspace_id,
        address.lower(),
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    return result


@app.post("/workspaces/{workspace_id}/nodes/{address}/notes")
def add_workspace_node_note(
    workspace_id: str,
    address: str,
    payload: NodeNoteIn,
):
    result = add_node_note(
        workspace_id,
        address.lower(),
        payload.text,
        payload.actor,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    return result


@app.post("/workspaces/{workspace_id}/report")
def workspace_report(workspace_id: str):
    workspace_data = get_workspace(workspace_id)

    if workspace_data is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    trace_id = workspace_data.get("traceId")

    if trace_id is None:
        raise HTTPException(
            status_code=404,
            detail="Trace not found for workspace.",
        )

    return {
        "trace_id": trace_id,
        "report_url": f"/api/report/{trace_id}",
    }
