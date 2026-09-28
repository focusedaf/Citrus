import { DEMO_NOW, ME, MEMBERS, WORKSPACES } from "./mock-data"
import { levelFromScore } from "./format"
import type { Alert, EntityType, GraphEdge, GraphNode, Workspace } from "./types"

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api"

/** Shape of POST /trace in backend/main.py */
interface TraceResponse {
  trace_id: number
  address: string
  edges: { from: string; to: string; token: string; amount: number; hop: number; timestamp: number; tx_hash: string; is_spoofed_token?: boolean }[]
  tags: Record<string, { entity_type: string; label: string; confidence?: string } | null>
  summary: {
    transactions_analyzed: number; unique_counterparties: number; max_trace_depth: number; assets_observed: string[]
    entity_findings: { vasp: string[] | string; bridge: string[] | string; mixer: string[] | string }
    spoofed_tokens_detected: string[] | string; cross_chain_activity: string[] | string
  }
  risk: { score: number; level: string; reasons: string[] }
  alert_raised: string | null
}

const arr = (v: string[] | string | undefined) => (Array.isArray(v) ? v : [])

export function fromTraceResponse(r: TraceResponse, complaintId?: string): { ws: Workspace; alert?: Alert } {
  const hopOf = new Map<string, number>([[r.address, 0]])
  r.edges.forEach((e) => { if (!hopOf.has(e.to)) hopOf.set(e.to, e.hop + 1) })
  const ids = new Set<string>([r.address, ...r.edges.flatMap((e) => [e.from, e.to])])
  const nodes: GraphNode[] = [...ids].map((id) => {
    const t = r.tags?.[id]
    const type: EntityType = id === r.address ? "reported" : ((t?.entity_type as EntityType) ?? "unknown")
    return { id, label: id === r.address ? "Victim-reported wallet" : (t?.label ?? "Unidentified"), type, hop: hopOf.get(id) ?? 1, confidence: (t?.confidence as GraphNode["confidence"]) ?? "n/a" }
  })
  const edges: GraphEdge[] = r.edges.map((e) => ({ ...e, is_spoofed_token: !!e.is_spoofed_token }))
  const ts = Math.floor(Date.now() / 1000)
  const idn = `CT-${1043 + Math.floor(Math.random() * 900)}`
  const id = idn
  const ws: Workspace = {
    id, traceId: r.trace_id, title: `Live trace – ${r.address.slice(0, 10)}…`,
    complaintId: complaintId ?? `NCRP/2026/LIVE/${String(r.trace_id).padStart(6, "0")}`, source: "NCRP/SAHYOG (mock)",
    victimState: "—", address: r.address, chain: "Ethereum", status: "Tracing",
    riskScore: r.risk.score, riskLevel: levelFromScore(r.risk.score), amountInr: 0, createdAt: ts,
    members: [ME], lead: ME, nodes, edges, reasons: r.risk.reasons,
    summary: {
      transactions: r.summary.transactions_analyzed, counterparties: r.summary.unique_counterparties, depth: r.summary.max_trace_depth,
      assets: r.summary.assets_observed, vasps: arr(r.summary.entity_findings.vasp), bridges: arr(r.summary.entity_findings.bridge),
      mixers: arr(r.summary.entity_findings.mixer), spoofed: arr(r.summary.spoofed_tokens_detected), crossChain: arr(r.summary.cross_chain_activity),
    },
    evidenceHash: "", comments: [],
    activity: [{ id: "a0", by: ME, at: ts, text: `ran live trace #${r.trace_id} against Etherscan` }],
    tasks: [],
    reports: [{ id: "r0", name: `Investigation report – trace ${r.trace_id}.pdf`, at: ts, by: ME, kind: "PDF" }],
  }
  const alert: Alert | undefined = r.alert_raised
    ? { id: `AL-${r.trace_id}`, workspaceId: id, address: r.address, level: ws.riskLevel, message: r.alert_raised.replace(/^ALERT \[[^\]]+\] /, ""), at: ts, acknowledged: false }
    : undefined
  return { ws, alert }
}

/** Try the real backend; if it's down (or key/quota fails) fall back to a demo trace so the demo never dies. */
export async function runTrace(address: string, maxHops: number): Promise<{ ws: Workspace; alert?: Alert; source: "live" | "demo" }> {
  try {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 45000)
    const res = await fetch(`${API_URL}/trace?address=${encodeURIComponent(address)}&max_hops=${maxHops}`, { method: "POST", signal: ctrl.signal })
    clearTimeout(timer)
    if (!res.ok) throw new Error(String(res.status))
    const data: TraceResponse = await res.json()
    if (!data.edges?.length) throw new Error("empty")
    return { ...fromTraceResponse(data), source: "live" }
  } catch {
    await new Promise((r) => setTimeout(r, 400))
    const tpl = WORKSPACES[2]
    const remap = (a: string) => (a === tpl.address ? address.toLowerCase() : a)
    const ts = Math.floor(Date.now() / 1000)
    const ws: Workspace = {
      ...tpl, id: `CT-${1043 + Math.floor(Math.random() * 900)}`, traceId: undefined, address: address.toLowerCase(),
      title: `Demo trace – ${address.slice(0, 10)}…`, complaintId: "NCRP/2026/DEMO/000001", status: "Tracing",
      createdAt: ts, members: [ME], lead: ME, comments: [], tasks: [],
      nodes: tpl.nodes.map((n) => ({ ...n, id: remap(n.id) })),
      edges: tpl.edges.map((e) => ({ ...e, from: remap(e.from), to: remap(e.to), timestamp: ts - (DEMO_NOW - e.timestamp) % 86400 })),
      activity: [{ id: "a0", by: ME, at: ts, text: "ran automated trace (demo dataset – backend unreachable)" }],
      reports: [],
    }
    return { ws, source: "demo" }
  }
}

export { MEMBERS }
