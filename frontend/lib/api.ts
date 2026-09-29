import { ME, MEMBERS } from "./mock-data";
import { levelFromScore } from "./format";
import type {
  Alert,
  EntityType,
  GraphEdge,
  GraphNode,
  Workspace,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

interface TraceResponse {
  trace_id: number;
  workspace_id: string;
  address: string;
  edges: {
    from: string;
    to: string;
    type?: string;
    token: string;
    amount: number;
    hop: number;
    timestamp: number;
    tx_hash: string;
    is_spoofed_token?: boolean;
    function_name?: string;
  }[];
  tags: Record<
    string,
    {
      entity_type: string;
      label: string;
      confidence?: string;
    } | null
  >;
  summary: {
    reported_address?: string;
    chain?: string;
    transactions_analyzed: number;
    unique_counterparties: number;
    max_trace_depth: number;
    assets_observed: string[];
    entity_findings: {
      vasp: string[] | string;
      bridge: string[] | string;
      mixer: string[] | string;
      known_contracts?: string[] | string;
      unidentified_wallets?: number;
    };
    spoofed_tokens_detected: string[] | string;
    cross_chain_activity: string[] | string;
  };
  risk: {
    score: number;
    level: string;
    reasons: string[];
  };
  alert_raised: string | null;
  report_url?: string | null;
  graph_url?: string | null;
  evidence_url?: string | null;
  blob_artifacts?: {
    report: string | null;
    graph: string | null;
    evidence: string | null;
  };
}

const arr = (v: string[] | string | undefined) => (Array.isArray(v) ? v : []);

const CHAIN_NAMES: Record<number, string> = {
  1: "Ethereum",
  56: "BNB Smart Chain",
  137: "Polygon",
  42161: "Arbitrum One",
  10: "Optimism",
  43114: "Avalanche C-Chain",
};

export function fromTraceResponse(
  r: TraceResponse,
  chainId: number,
): { ws: Workspace; alert?: Alert } {
  const hopOf = new Map<string, number>([[r.address, 0]]);

  r.edges.forEach((e) => {
    if (!hopOf.has(e.to)) {
      hopOf.set(e.to, e.hop + 1);
    }
  });

  const ids = new Set<string>([
    r.address,
    ...r.edges.flatMap((e) => [e.from, e.to]),
  ]);

  const nodes: GraphNode[] = [...ids].map((id) => {
    const t = r.tags?.[id];

    const type: EntityType =
      id === r.address
        ? "reported"
        : ((t?.entity_type as EntityType) ?? "unknown");

    return {
      id,
      label:
        id === r.address
          ? "Victim-reported wallet"
          : (t?.label ?? "Unidentified"),
      type,
      hop: hopOf.get(id) ?? 1,
      confidence: (t?.confidence as GraphNode["confidence"]) ?? "n/a",
    };
  });

  const edges: GraphEdge[] = r.edges.map((e) => ({
    ...e,
    is_spoofed_token: !!e.is_spoofed_token,
  }));

  const ts = Math.floor(Date.now() / 1000);

  const ws: Workspace = {
    id: r.workspace_id,
    traceId: r.trace_id,
    title: `Live trace – ${r.address.slice(0, 10)}…`,
    complaintId: `NCRP/2026/LIVE/${String(r.trace_id).padStart(6, "0")}`,
    source: "NCRP/SAHYOG (mock)",
    victimState: "—",
    address: r.address,
    chain: r.summary.chain ?? CHAIN_NAMES[chainId] ?? `Chain ${chainId}`,
    status: "Tracing",
    riskScore: r.risk.score,
    riskLevel: levelFromScore(r.risk.score),
    amountInr: 0,
    createdAt: ts,
    members: [ME],
    lead: ME,
    nodes,
    edges,
    reasons: r.risk.reasons,
    summary: {
      transactions: r.summary.transactions_analyzed,
      counterparties: r.summary.unique_counterparties,
      depth: r.summary.max_trace_depth,
      assets: r.summary.assets_observed,
      vasps: arr(r.summary.entity_findings.vasp),
      bridges: arr(r.summary.entity_findings.bridge),
      mixers: arr(r.summary.entity_findings.mixer),
      spoofed: arr(r.summary.spoofed_tokens_detected),
      crossChain: arr(r.summary.cross_chain_activity),
    },
    evidenceHash: "",
    comments: [],
    activity: [
      {
        id: "a0",
        by: ME,
        at: ts,
        text: `ran live trace #${r.trace_id}`,
      },
    ],
    tasks: [],
    reports: r.blob_artifacts?.report
      ? [
          {
            id: `r-${r.trace_id}`,
            name: `Investigation report – trace ${r.trace_id}.pdf`,
            at: ts,
            by: ME,
            kind: "PDF",
          },
        ]
      : [],
  };

  const alert: Alert | undefined = r.alert_raised
    ? {
        id: `AL-${r.trace_id}`,
        workspaceId: r.workspace_id,
        address: r.address,
        level: ws.riskLevel,
        message: r.alert_raised.replace(/^ALERT \[[^\]]+\] /, ""),
        at: ts,
        acknowledged: false,
      }
    : undefined;

  return { ws, alert };
}

export async function runTrace(
  address: string,
  maxHops: number,
  chainId = 1,
): Promise<{
  ws: Workspace;
  alert?: Alert;
  source: "live";
}> {
  const ctrl = new AbortController();

  const timer = setTimeout(() => ctrl.abort(), 60000);

  try {
    const params = new URLSearchParams({
      address,
      chain_id: String(chainId),
      max_hops: String(maxHops),
      check_cross_chain: "true",
    });

    const res = await fetch(`${API_URL}/trace?${params.toString()}`, {
      method: "POST",
      signal: ctrl.signal,
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => "");
      throw new Error(
        `Trace request failed (${res.status})${errorText ? `: ${errorText}` : ""}`,
      );
    }

    const data: TraceResponse = await res.json();

    return {
      ...fromTraceResponse(data, chainId),
      source: "live",
    };
  } finally {
    clearTimeout(timer);
  }
}

export async function getWorkspaces(limit = 100) {
  const res = await fetch(`${API_URL}/workspaces?limit=${limit}`);

  if (!res.ok) {
    throw new Error(`Failed to load workspaces (${res.status})`);
  }

  return res.json();
}

export async function getWorkspace(workspaceId: string) {
  const res = await fetch(
    `${API_URL}/workspaces/${encodeURIComponent(workspaceId)}`,
  );

  if (!res.ok) {
    throw new Error(`Failed to load workspace (${res.status})`);
  }

  return res.json();
}

export async function updateWorkspaceStatus(
  workspaceId: string,
  status: string,
  actor = "m1",
) {
  const res = await fetch(
    `${API_URL}/workspaces/${encodeURIComponent(workspaceId)}/status`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        status,
        actor,
      }),
    },
  );

  if (!res.ok) {
    throw new Error(`Failed to update workspace status (${res.status})`);
  }

  return res.json();
}

export async function addComment(
  workspaceId: string,
  text: string,
  actor = "m1",
) {
  const res = await fetch(
    `${API_URL}/workspaces/${encodeURIComponent(workspaceId)}/comments`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        actor,
      }),
    },
  );

  if (!res.ok) {
    throw new Error(`Failed to add comment (${res.status})`);
  }

  return res.json();
}

export async function addTask(
  workspaceId: string,
  text: string,
  assignee = "m1",
  actor = "m1",
) {
  const res = await fetch(
    `${API_URL}/workspaces/${encodeURIComponent(workspaceId)}/tasks`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        assignee,
        actor,
      }),
    },
  );

  if (!res.ok) {
    throw new Error(`Failed to add task (${res.status})`);
  }

  return res.json();
}

export async function toggleTask(
  workspaceId: string,
  taskId: string,
  actor = "m1",
) {
  const params = new URLSearchParams({ actor });

  const res = await fetch(
    `${API_URL}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/tasks/${encodeURIComponent(taskId)}?${params.toString()}`,
    {
      method: "PATCH",
    },
  );

  if (!res.ok) {
    throw new Error(`Failed to toggle task (${res.status})`);
  }

  return res.json();
}

export async function inviteMember(
  workspaceId: string,
  memberId: string,
  actor = "m1",
) {
  const res = await fetch(
    `${API_URL}/workspaces/${encodeURIComponent(workspaceId)}/members`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        member_id: memberId,
        actor,
      }),
    },
  );

  if (!res.ok) {
    throw new Error(`Failed to invite member (${res.status})`);
  }

  return res.json();
}

export async function flagNode(
  workspaceId: string,
  address: string,
  actor = "m1",
) {
  const res = await fetch(
    `${API_URL}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/nodes/${encodeURIComponent(address)}/flag?actor=${encodeURIComponent(
      actor,
    )}`,
    {
      method: "POST",
    },
  );

  if (!res.ok) {
    throw new Error(`Failed to flag node (${res.status})`);
  }

  return res.json();
}

export async function addNodeNote(
  workspaceId: string,
  address: string,
  text: string,
  actor = "m1",
) {
  const res = await fetch(
    `${API_URL}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/nodes/${encodeURIComponent(address)}/notes`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        actor,
      }),
    },
  );

  if (!res.ok) {
    throw new Error(`Failed to add node note (${res.status})`);
  }

  return res.json();
}

export async function acknowledgeAlert(alertId: string) {
  const res = await fetch(
    `${API_URL}/alerts/${encodeURIComponent(alertId)}/ack`,
    {
      method: "PATCH",
    },
  );

  if (!res.ok) {
    throw new Error(`Failed to acknowledge alert (${res.status})`);
  }

  return res.json();
}

export async function getAlerts(limit = 50) {
  const res = await fetch(`${API_URL}/alerts?limit=${limit}`);

  if (!res.ok) {
    throw new Error(`Failed to load alerts (${res.status})`);
  }

  return res.json();
}

export async function getDashboardStats(days = 30) {
  const res = await fetch(`${API_URL}/dashboard/stats?days=${days}`);

  if (!res.ok) {
    throw new Error(`Failed to load dashboard stats (${res.status})`);
  }

  return res.json();
}

export async function getTraceGraph(traceId: number) {
  const res = await fetch(`${API_URL}/graph/${traceId}`);

  if (!res.ok) {
    throw new Error(`Failed to load graph (${res.status})`);
  }

  return res.text();
}

export async function getEvidence(traceId: number) {
  const res = await fetch(`${API_URL}/evidence/${traceId}`);

  if (!res.ok) {
    throw new Error(`Failed to load evidence (${res.status})`);
  }

  return res.json();
}

export async function verifyEvidence(traceId: number) {
  const res = await fetch(`${API_URL}/evidence/${traceId}/verify`);

  if (!res.ok) {
    throw new Error(`Failed to verify evidence (${res.status})`);
  }

  return res.json();
}

export async function getReport(traceId: number) {
  const res = await fetch(`${API_URL}/report/${traceId}`);

  if (!res.ok) {
    throw new Error(`Failed to load report (${res.status})`);
  }

  return res.blob();
}

export async function getReports(limit = 100) {
  const res = await fetch(`${API_URL}/reports?limit=${limit}`);

  if (!res.ok) {
    throw new Error(`Failed to load reports (${res.status})`);
  }

  return res.json();
}

export async function getTraces(limit = 50) {
  const res = await fetch(`${API_URL}/traces?limit=${limit}`);

  if (!res.ok) {
    throw new Error(`Failed to load traces (${res.status})`);
  }

  return res.json();
}

export async function getMembers() {
  const res = await fetch(`${API_URL}/members`);

  if (!res.ok) {
    throw new Error(`Failed to load members (${res.status})`);
  }

  return res.json();
}

export { MEMBERS };
