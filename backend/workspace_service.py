"""Persistent investigation-workspace API helpers.

A trace is the immutable blockchain-analysis result. A workspace is the
human-investigation layer built around that trace: status, collaboration,
comments, tasks and node annotations.
"""
import time
import uuid
from db import get_connection

VALID_STATUSES = {"New", "Tracing", "In Review", "Freeze Requested", "Closed"}

MEMBERS = [
    {"id": "m1", "name": "Insp. Aarav Mehta", "role": "Lead", "org": "Cyber Cell, Pune", "online": True},
    {"id": "m2", "name": "Asha Nair", "role": "Analyst", "org": "I4C, MHA", "online": True},
    {"id": "m3", "name": "Rohan Iyer", "role": "Forensics", "org": "State FSL, Mumbai", "online": False},
    {"id": "m4", "name": "Priya Deshmukh", "role": "Legal", "org": "Nodal Officer, NCRP", "online": True},
    {"id": "m5", "name": "Kabir Singh", "role": "Liaison", "org": "VASP Compliance Desk", "online": False},
]


def _now():
    return int(time.time())


def _workspace_id(trace_id: int) -> str:
    return f"CT-{1000 + trace_id}"


def ensure_workspace(
    trace_id,
    address,
    chain=None,
    chain_id=None,
    risk=None,
    complaint_id=None,
    source="NCRP/SAHYOG (mock)",
):
    # Keep chain_id as the canonical blockchain identifier while preserving
    # the existing `chain` database column used by the workspace UI.
    if chain_id is not None:
        from config import SUPPORTED_CHAINS
        chain = SUPPORTED_CHAINS.get(chain_id, f"Chain {chain_id}")
    if chain is None:
        chain = "Unknown"

    wid = _workspace_id(trace_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM workspaces WHERE id=%s", (wid,))
        if cur.fetchone():
            return wid
        ts = _now()
        cur.execute("""
            INSERT INTO workspaces
              (id, trace_id, title, complaint_id, source, victim_state, chain,
               status, amount_inr, created_at, lead)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (wid, trace_id, f"Live trace – {address[:10]}…", complaint_id or f"NCRP/2026/LIVE/{trace_id:06d}", source, "—", chain, "Tracing", 0, ts, "m1"))
        cur.execute("INSERT INTO workspace_members(workspace_id, member_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (wid, "m1"))
        cur.execute("INSERT INTO workspace_activity(workspace_id, by_member, text, at) VALUES (%s,%s,%s,%s)", (wid, "m1", f"created this workspace from trace {trace_id}", ts))
        conn.commit()
    return wid


def _node_records(ws, trace):
    edges = trace.get("edges_json") or []
    tags = trace.get("tags_json") or {}
    addresses = {trace["address"]}
    for e in edges:
        addresses.add(e.get("from", "")); addresses.add(e.get("to", ""))
    addresses.discard("")
    hop = {trace["address"]: 0}
    for e in edges:
        hop.setdefault(e.get("to"), int(e.get("hop", 0)) + 1)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT address, flagged, notes_json FROM workspace_nodes WHERE workspace_id=%s", (ws["id"],))
        annotations = {r[0]: (r[1], r[2] or []) for r in cur.fetchall()}
    out = []
    for address in sorted(addresses):
        tag = tags.get(address)
        if tag:
            typ = tag.get("entity_type", "unknown")
            label = tag.get("label", "Unidentified")
            confidence = tag.get("confidence", "n/a")
        else:
            typ, label, confidence = ("reported", "Victim-reported wallet", "n/a") if address == trace["address"] else ("unknown", "Unidentified", "n/a")
        flagged, notes = annotations.get(address, (False, []))
        out.append({"id": address, "label": label, "type": typ, "hop": hop.get(address, 1), "confidence": confidence, "flagged": flagged, "notes": notes})
    return out


def _edge_records(trace):
    return trace.get("edges_json") or []


def _members(wid):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT member_id FROM workspace_members WHERE workspace_id=%s ORDER BY member_id", (wid,))
        return [r[0] for r in cur.fetchall()]


def workspace_dict(trace, ws):
    summary = trace.get("summary_json") or {}
    risk_score = trace.get("risk_score") or 0
    risk_level = trace.get("risk_level") or "Low"
    findings = summary.get("entity_findings") or {}
    as_list = lambda v: v if isinstance(v, list) else []
    alerts = []
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, risk_level, message, created_at, acknowledged FROM alerts WHERE trace_id=%s ORDER BY created_at DESC", (trace["id"],))
        alerts = [{"id": f"AL-{r[0]}", "workspaceId": ws["id"], "address": trace["address"], "level": r[1], "message": r[2], "at": r[3], "acknowledged": r[4]} for r in cur.fetchall()]
        cur.execute("SELECT id, by_member, text, at FROM workspace_comments WHERE workspace_id=%s ORDER BY at ASC", (ws["id"],))
        comments = [{"id": str(r[0]), "by": r[1], "text": r[2], "at": r[3]} for r in cur.fetchall()]
        cur.execute("SELECT id, text, assignee, done FROM workspace_tasks WHERE workspace_id=%s ORDER BY created_at ASC", (ws["id"],))
        tasks = [{"id": str(r[0]), "text": r[1], "assignee": r[2], "done": r[3]} for r in cur.fetchall()]
        cur.execute("SELECT id, by_member, text, at FROM workspace_activity WHERE workspace_id=%s ORDER BY at DESC", (ws["id"],))
        activity = [{"id": str(r[0]), "by": r[1], "text": r[2], "at": r[3]} for r in cur.fetchall()]
    return {
        "id": ws["id"], "traceId": trace["id"], "title": ws["title"], "complaintId": ws["complaint_id"],
        "source": ws["source"], "victimState": ws["victim_state"], "address": trace["address"],
        "chain": ws["chain"],
        "chainId": trace.get("chain_id"),
        "status": ws["status"], "riskScore": risk_score, "riskLevel": risk_level,
        "amountInr": ws["amount_inr"] or 0, "createdAt": ws["created_at"], "members": _members(ws["id"]),
        "lead": ws["lead"], "nodes": _node_records(ws, trace), "edges": _edge_records(trace),
        "reasons": (summary.get("risk_indicators") or []),
        "summary": {
            "transactions": summary.get("transactions_analyzed", 0), "counterparties": summary.get("unique_counterparties", 0),
            "depth": summary.get("max_trace_depth", 0), "assets": summary.get("assets_observed", []),
            "vasps": as_list(findings.get("vasp")), "bridges": as_list(findings.get("bridge")),
            "mixers": as_list(findings.get("mixer")), "spoofed": as_list(summary.get("spoofed_tokens_detected")),
            "crossChain": as_list(summary.get("cross_chain_activity")),
        },
        "evidenceHash": trace.get("evidence_hash") or "", "comments": comments, "activity": activity,
        "tasks": tasks,
        "reports": [{"id": f"r-{trace['id']}", "name": f"Investigation report – trace {trace['id']}.pdf", "at": trace["created_at"], "by": ws["lead"], "kind": "PDF"}],
        "alerts": alerts,
    }


def get_workspace(workspace_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM workspaces WHERE id=%s", (workspace_id,))
        ws = cur.fetchone()
        if not ws:
            return None
        cols = [d[0] for d in cur.description]
        ws = dict(zip(cols, ws))
        cur.execute("SELECT * FROM traces WHERE id=%s", (ws["trace_id"],))
        row = cur.fetchone()
        cols = [d[0] for d in cur.description]
        trace = dict(zip(cols, row)) if row else None
    return workspace_dict(trace, ws) if trace else None


def list_workspaces(limit=20):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM workspaces ORDER BY created_at DESC LIMIT %s",
            (min(limit, 20),),
        )
        rows = cur.fetchall(); cols = [d[0] for d in cur.description]
    result=[]
    for row in rows:
        ws=dict(zip(cols,row))
        with get_connection() as conn:
            cur=conn.cursor(); cur.execute("SELECT * FROM traces WHERE id=%s", (ws["trace_id"],)); tr=cur.fetchone(); tc=[d[0] for d in cur.description]
        if tr: result.append(workspace_dict(dict(zip(tc,tr)),ws))
    return result


def _activity(cur, wid, actor, text):
    cur.execute("INSERT INTO workspace_activity(workspace_id, by_member, text, at) VALUES (%s,%s,%s,%s)", (wid, actor, text, _now()))


def update_status(wid, status, actor="m1"):
    if status not in VALID_STATUSES: raise ValueError("Invalid case status")
    with get_connection() as conn:
        cur=conn.cursor(); cur.execute("UPDATE workspaces SET status=%s WHERE id=%s RETURNING id", (status,wid));
        if not cur.fetchone(): return False
        _activity(cur,wid,actor,f"changed status to “{status}”"); conn.commit(); return True


def add_comment(wid,text,actor="m1"):
    with get_connection() as conn:
        cur=conn.cursor(); cid=str(uuid.uuid4()); ts=_now(); cur.execute("INSERT INTO workspace_comments(id,workspace_id,by_member,text,at) VALUES (%s,%s,%s,%s,%s)",(cid,wid,actor,text,ts)); _activity(cur,wid,actor,"commented on the case"); conn.commit(); return cid


def add_task(wid,text,assignee="m1",actor="m1"):
    with get_connection() as conn:
        cur=conn.cursor(); tid=str(uuid.uuid4()); ts=_now(); cur.execute("INSERT INTO workspace_tasks(id,workspace_id,text,assignee,done,created_at) VALUES (%s,%s,%s,%s,false,%s)",(tid,wid,text,assignee,ts)); _activity(cur,wid,actor,f'added task “{text}”'); conn.commit(); return tid


def toggle_task(wid,task_id,actor="m1"):
    with get_connection() as conn:
        cur=conn.cursor(); cur.execute("UPDATE workspace_tasks SET done=NOT done WHERE id=%s AND workspace_id=%s RETURNING done",(task_id,wid)); r=cur.fetchone();
        if not r: return None
        _activity(cur,wid,actor,"updated a task"); conn.commit(); return r[0]


def invite_member(wid,member_id,actor="m1"):
    if member_id not in {m["id"] for m in MEMBERS}: raise ValueError("Unknown member")
    with get_connection() as conn:
        cur=conn.cursor(); cur.execute("INSERT INTO workspace_members(workspace_id,member_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",(wid,member_id)); _activity(cur,wid,actor,f"invited {member_id} to the workspace"); conn.commit()


def acknowledge_alert(alert_id):
    # frontend uses AL-{serial id}; accept either form
    raw = int(str(alert_id).replace("AL-", ""))
    with get_connection() as conn:
        cur=conn.cursor(); cur.execute("UPDATE alerts SET acknowledged=true WHERE id=%s RETURNING id",(raw,)); r=cur.fetchone(); conn.commit(); return bool(r)


def toggle_node_flag(wid,address,actor="m1"):
    with get_connection() as conn:
        cur=conn.cursor(); cur.execute("INSERT INTO workspace_nodes(workspace_id,address,flagged,notes_json) VALUES (%s,%s,true,'[]'::jsonb) ON CONFLICT (workspace_id,address) DO UPDATE SET flagged=NOT workspace_nodes.flagged RETURNING flagged",(wid,address)); r=cur.fetchone(); _activity(cur,wid,actor,f"flagged {address[:10]}… for freeze request"); conn.commit(); return r[0]


def add_node_note(wid,address,text,actor="m1"):
    with get_connection() as conn:
        cur=conn.cursor(); cur.execute("SELECT notes_json FROM workspace_nodes WHERE workspace_id=%s AND address=%s",(wid,address)); r=cur.fetchone(); notes=(r[0] if r else []) or []; notes.append({"by":actor,"text":text,"at":_now()}); cur.execute("INSERT INTO workspace_nodes(workspace_id,address,flagged,notes_json) VALUES (%s,%s,false,%s) ON CONFLICT (workspace_id,address) DO UPDATE SET notes_json=EXCLUDED.notes_json",(wid,address,__import__('json').dumps(notes))); _activity(cur,wid,actor,f"annotated {address[:10]}…"); conn.commit()
