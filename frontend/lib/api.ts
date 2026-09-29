import { ME, MEMBERS } from "./mock-data"
import { levelFromScore } from "./format"

import type {
  Alert,
  EntityType,
  GraphEdge,
  GraphNode,
  Workspace,
} from "./types"

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "/api"

interface TraceResponse {
  trace_id: number
  workspace_id: string
  address: string

  edges: {
    from: string
    to: string
    type?: string
    token: string
    amount: number
    hop: number
    timestamp: number
    tx_hash: string
    is_spoofed_token?: boolean
    function_name?: string
  }[]

  tags: Record<
    string,
    {
      entity_type: string
      label: string
      confidence?: string
    } | null
  >

  summary: {
    reported_address?: string
    chain?: string
    transactions_analyzed: number
    unique_counterparties: number
    max_trace_depth: number
    assets_observed: string[]

    entity_findings: {
      vasp: string[] | string
      bridge: string[] | string
      mixer: string[] | string
      known_contracts?: string[] | string
      unidentified_wallets?: number
    }

    spoofed_tokens_detected: string[] | string
    cross_chain_activity: string[] | string
  }

  risk: {
    score: number
    level: string
    reasons: string[]
  }

  alert_raised: string | null

  report_url?: string | null
  graph_url?: string | null
  evidence_url?: string | null

  blob_artifacts?: {
    report: string | null
    graph: string | null
    evidence: string | null
  }
}

const arr = (
  value: string[] | string | undefined
): string[] => {
  return Array.isArray(value) ? value : []
}

const CHAIN_NAMES: Record<number, string> = {
  1: "Ethereum",
  56: "BNB Smart Chain",
  137: "Polygon",
  42161: "Arbitrum One",
  10: "Optimism",
  43114: "Avalanche C-Chain",
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  })

  if (!res.ok) {
    const text = await res.text().catch(() => "")

    throw new Error(
      `${options?.method ?? "GET"} ${path} failed (${res.status})${
        text ? `: ${text}` : ""
      }`
    )
  }

  return res.json()
}

export function fromTraceResponse(
  r: TraceResponse,
  chainId = 1,
  complaintId?: string
): {
  ws: Workspace
  alert?: Alert
} {
  const hopOf = new Map<string, number>([
    [r.address, 0],
  ])

  r.edges.forEach((edge) => {
    if (!hopOf.has(edge.to)) {
      hopOf.set(edge.to, edge.hop + 1)
    }
  })

  const ids = new Set<string>([
    r.address,
    ...r.edges.flatMap((edge) => [
      edge.from,
      edge.to,
    ]),
  ])

  const nodes: GraphNode[] = [...ids].map((id) => {
    const tag = r.tags?.[id]

    const type: EntityType =
      id === r.address
        ? "reported"
        : ((tag?.entity_type as EntityType) ?? "unknown")

    return {
      id,
      label:
        id === r.address
          ? "Victim-reported wallet"
          : (tag?.label ?? "Unidentified"),
      type,
      hop: hopOf.get(id) ?? 1,
      confidence:
        (tag?.confidence as GraphNode["confidence"]) ??
        "n/a",
    }
  })

  const edges: GraphEdge[] = r.edges.map((edge) => ({
    ...edge,
    is_spoofed_token: !!edge.is_spoofed_token,
  }))

  const timestamp = Math.floor(Date.now() / 1000)

  const workspace: Workspace = {
    id: r.workspace_id,
    traceId: r.trace_id,

    title: `Live trace – ${r.address.slice(0, 10)}…`,

    complaintId:
      complaintId ??
      `NCRP/2026/LIVE/${String(r.trace_id).padStart(
        6,
        "0"
      )}`,

    source: "NCRP/SAHYOG",

    victimState: "—",

    address: r.address,

    chain:
      r.summary.chain ??
      CHAIN_NAMES[chainId] ??
      `Chain ${chainId}`,

    status: "Tracing",

    riskScore: r.risk.score,

    riskLevel: levelFromScore(r.risk.score),

    amountInr: 0,

    createdAt: timestamp,

    members: [ME],

    lead: ME,

    nodes,

    edges,

    reasons: r.risk.reasons,

    summary: {
      transactions:
        r.summary.transactions_analyzed,

      counterparties:
        r.summary.unique_counterparties,

      depth:
        r.summary.max_trace_depth,

      assets:
        r.summary.assets_observed,

      vasps:
        arr(r.summary.entity_findings.vasp),

      bridges:
        arr(r.summary.entity_findings.bridge),

      mixers:
        arr(r.summary.entity_findings.mixer),

      spoofed:
        arr(r.summary.spoofed_tokens_detected),

      crossChain:
        arr(r.summary.cross_chain_activity),
    },

    evidenceHash: "",

    comments: [],

    activity: [
      {
        id: "a0",
        by: ME,
        at: timestamp,
        text: `ran live trace #${r.trace_id}`,
      },
    ],

    tasks: [],

    reports: r.blob_artifacts?.report
      ? [
          {
            id: `r-${r.trace_id}`,
            name: `Investigation report – trace ${r.trace_id}.pdf`,
            at: timestamp,
            by: ME,
            kind: "PDF",
          },
        ]
      : [],
  }

  const alert: Alert | undefined = r.alert_raised
    ? {
        id: `AL-${r.trace_id}`,
        workspaceId: r.workspace_id,
        address: r.address,
        level: workspace.riskLevel,
        message: r.alert_raised.replace(
          /^ALERT \[[^\]]+\] /,
          ""
        ),
        at: timestamp,
        acknowledged: false,
      }
    : undefined

  return {
    ws: workspace,
    alert,
  }
}

export async function runTrace(
  address: string,
  maxHops: number,
  chainId = 1
): Promise<{
  ws: Workspace
  alert?: Alert
  source: "live"
}> {
  const controller = new AbortController()

  const timer = setTimeout(
    () => controller.abort(),
    60000
  )

  try {
    const params = new URLSearchParams({
      address,
      chain_id: String(chainId),
      max_hops: String(maxHops),
      check_cross_chain: "true",
    })

    const res = await fetch(
      `${API_URL}/trace?${params.toString()}`,
      {
        method: "POST",
        signal: controller.signal,
      }
    )

    if (!res.ok) {
      const errorText = await res
        .text()
        .catch(() => "")

      throw new Error(
        `Trace request failed (${res.status})${
          errorText ? `: ${errorText}` : ""
        }`
      )
    }

    const data: TraceResponse = await res.json()

    if (!data.trace_id) {
      throw new Error(
        "Backend returned an invalid trace response."
      )
    }

    return {
      ...fromTraceResponse(data, chainId),
      source: "live",
    }
  } finally {
    clearTimeout(timer)
  }
}

export async function getWorkspaces(
  limit = 100
): Promise<Workspace[]> {
  return request<Workspace[]>(
    `/workspaces?limit=${limit}`
  )
}

export async function getWorkspace(
  workspaceId: string
): Promise<Workspace> {
  return request<Workspace>(
    `/workspaces/${encodeURIComponent(workspaceId)}`
  )
}

export async function getAlerts(
  limit = 50
): Promise<Alert[]> {
  return request<Alert[]>(
    `/alerts?limit=${limit}`
  )
}

export async function getMembers() {
  return request<typeof MEMBERS>("/members")
}

export async function updateStatus(
  workspaceId: string,
  status: string,
  actor = ME
): Promise<Workspace> {
  return request<Workspace>(
    `/workspaces/${encodeURIComponent(
      workspaceId
    )}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({
        status,
        actor,
      }),
    }
  )
}

export async function addComment(
  workspaceId: string,
  text: string,
  actor = ME
): Promise<Workspace> {
  return request<Workspace>(
    `/workspaces/${encodeURIComponent(
      workspaceId
    )}/comments`,
    {
      method: "POST",
      body: JSON.stringify({
        text,
        actor,
      }),
    }
  )
}

export async function addTask(
  workspaceId: string,
  text: string,
  assignee = ME,
  actor = ME
): Promise<Workspace> {
  return request<Workspace>(
    `/workspaces/${encodeURIComponent(
      workspaceId
    )}/tasks`,
    {
      method: "POST",
      body: JSON.stringify({
        text,
        assignee,
        actor,
      }),
    }
  )
}

export async function toggleTask(
  workspaceId: string,
  taskId: string,
  actor = ME
): Promise<Workspace> {
  return request<Workspace>(
    `/workspaces/${encodeURIComponent(
      workspaceId
    )}/tasks/${encodeURIComponent(
      taskId
    )}?actor=${encodeURIComponent(actor)}`,
    {
      method: "PATCH",
    }
  )
}

export async function inviteMember(
  workspaceId: string,
  memberId: string,
  actor = ME
): Promise<Workspace> {
  return request<Workspace>(
    `/workspaces/${encodeURIComponent(
      workspaceId
    )}/members`,
    {
      method: "POST",
      body: JSON.stringify({
        member_id: memberId,
        actor,
      }),
    }
  )
}

export async function acknowledgeAlert(
  alertId: string
): Promise<{
  ok: boolean
  alert_id: string
}> {
  return request<{
    ok: boolean
    alert_id: string
  }>(
    `/alerts/${encodeURIComponent(alertId)}/ack`,
    {
      method: "PATCH",
    }
  )
}

export async function flagNode(
  workspaceId: string,
  address: string,
  actor = ME
): Promise<{
  flagged: boolean
  workspace: Workspace
}> {
  return request<{
    flagged: boolean
    workspace: Workspace
  }>(
    `/workspaces/${encodeURIComponent(
      workspaceId
    )}/nodes/${encodeURIComponent(
      address
    )}/flag?actor=${encodeURIComponent(actor)}`,
    {
      method: "POST",
    }
  )
}

export async function addNodeNote(
  workspaceId: string,
  address: string,
  text: string,
  actor = ME
): Promise<Workspace> {
  return request<Workspace>(
    `/workspaces/${encodeURIComponent(
      workspaceId
    )}/nodes/${encodeURIComponent(
      address
    )}/notes`,
    {
      method: "POST",
      body: JSON.stringify({
        text,
        actor,
      }),
    }
  )
}

export async function generateReport(
  workspaceId: string
): Promise<{
  trace_id: number
  report_url: string
}> {
  return request<{
    trace_id: number
    report_url: string
  }>(
    `/workspaces/${encodeURIComponent(
      workspaceId
    )}/report`,
    {
      method: "POST",
    }
  )
}

export function getReportUrl(
  traceId: number
): string {
  return `${API_URL}/report/${traceId}`
}

export function getEvidenceUrl(
  traceId: number
): string {
  return `${API_URL}/evidence/${traceId}`
}

export function getGraphUrl(
  traceId: number
): string {
  return `${API_URL}/graph/${traceId}`
}

export async function getTraceGraph(
  traceId: number
) {
  const res = await fetch(
    `${API_URL}/graph/${traceId}`
  )

  if (!res.ok) {
    throw new Error(
      `Failed to load graph (${res.status})`
    )
  }

  return res.text()
}

export async function getEvidence(
  traceId: number
) {
  const res = await fetch(
    `${API_URL}/evidence/${traceId}`
  )

  if (!res.ok) {
    throw new Error(
      `Failed to load evidence (${res.status})`
    )
  }

  return res.json()
}

export async function verifyEvidence(
  traceId: number
): Promise<{
  exists: boolean
  valid?: boolean
  hash?: string
  message?: string
  [key: string]: unknown
}> {
  return request(
    `/evidence/${traceId}/verify`
  )
}

export async function getReport(
  traceId: number
) {
  const res = await fetch(
    `${API_URL}/report/${traceId}`
  )

  if (!res.ok) {
    throw new Error(
      `Failed to load report (${res.status})`
    )
  }

  return res.blob()
}

export async function getReports(
  limit = 100
) {
  return request(
    `/reports?limit=${limit}`
  )
}

export async function getTraces(
  limit = 50
) {
  return request(
    `/traces?limit=${limit}`
  )
}

export async function getDashboardStats(
  days = 30
) {
  return request(
    `/dashboard/stats?days=${days}`
  )
}

export { MEMBERS }