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

  edges?: {
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

  tags?: Record<
    string,
    {
      entity_type: string;
      label: string;
      confidence?: string;
    } | null
  >;

  summary?: {
    reported_address?: string;
    chain?: string;
    transactions_analyzed?: number;
    unique_counterparties?: number;
    max_trace_depth?: number;
    assets_observed?: string[];

    entity_findings?: {
      vasp?: string[] | string;
      bridge?: string[] | string;
      mixer?: string[] | string;
      known_contracts?: string[] | string;
      unidentified_wallets?: number;
    };

    spoofed_tokens_detected?: string[] | string;
    cross_chain_activity?: string[] | string;
  };

  risk?: {
    score?: number;
    level?: string;
    reasons?: string[];
  };

  alert_raised?: string | null;

  report_url?: string | null;
  graph_url?: string | null;
  evidence_url?: string | null;

  blob_artifacts?: {
    report?: string | null;
    graph?: string | null;
    evidence?: string | null;
  };
}

const arr = (
  value: string[] | string | undefined,
): string[] => {
  if (Array.isArray(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim().length > 0) {
    return [value];
  }

  return [];
};

const CHAIN_NAMES: Record<number, string> = {
  1: "Ethereum",
  56: "BNB Smart Chain",
  137: "Polygon",
  42161: "Arbitrum One",
  10: "Optimism",
  43114: "Avalanche C-Chain",
};

function requireTraceId(traceId: number): number {
  if (
    typeof traceId !== "number" ||
    !Number.isFinite(traceId) ||
    traceId <= 0
  ) {
    throw new Error(
      `Invalid trace ID: ${String(traceId)}`,
    );
  }

  return traceId;
}

function requireWorkspaceId(
  workspaceId: string,
): string {
  if (
    typeof workspaceId !== "string" ||
    workspaceId.trim().length === 0
  ) {
    throw new Error("Invalid workspace ID.");
  }

  return workspaceId;
}

function requireAddress(address: string): string {
  if (
    typeof address !== "string" ||
    address.trim().length === 0
  ) {
    throw new Error("Wallet address is required.");
  }

  return address.trim();
}

async function getErrorMessage(
  res: Response,
): Promise<string> {
  try {
    const contentType =
      res.headers.get("content-type") ?? "";

    if (contentType.includes("application/json")) {
      const data = await res.json().catch(() => null);

      if (typeof data?.detail === "string") {
        return data.detail;
      }

      if (typeof data?.message === "string") {
        return data.message;
      }

      if (data?.detail?.message) {
        return String(data.detail.message);
      }

      return JSON.stringify(data);
    }

    return await res.text().catch(() => "");
  } catch {
    return "";
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await getErrorMessage(res);

    throw new Error(
      `${options?.method ?? "GET"} ${path} failed (${res.status})${
        text ? `: ${text}` : ""
      }`,
    );
  }

  const contentType =
    res.headers.get("content-type") ?? "";

  if (res.status === 204) {
    return undefined as T;
  }

  if (!contentType.includes("application/json")) {
    throw new Error(
      `${options?.method ?? "GET"} ${path} returned an unexpected response type.`,
    );
  }

  return res.json() as Promise<T>;
}

export function fromTraceResponse(
  r: TraceResponse,
  chainId = 1,
  complaintId?: string,
): {
  ws: Workspace;
  alert?: Alert;
} {
  if (!r) {
    throw new Error(
      "Backend returned an empty trace response.",
    );
  }

  if (
    typeof r.trace_id !== "number" ||
    !Number.isFinite(r.trace_id)
  ) {
    throw new Error(
      "Backend returned an invalid trace ID.",
    );
  }

  if (
    typeof r.workspace_id !== "string" ||
    !r.workspace_id
  ) {
    throw new Error(
      "Backend returned an invalid workspace ID.",
    );
  }

  if (
    typeof r.address !== "string" ||
    !r.address
  ) {
    throw new Error(
      "Backend returned an invalid wallet address.",
    );
  }

  const summary = r.summary ?? {};
  const entityFindings =
    summary.entity_findings ?? {};

  const edgesData = r.edges ?? [];
  const tagsData = r.tags ?? {};

  const riskScore =
    typeof r.risk?.score === "number" &&
    Number.isFinite(r.risk.score)
      ? r.risk.score
      : 0;

  const hopOf = new Map<string, number>([
    [r.address, 0],
  ]);

  for (const edge of edgesData) {
    if (!hopOf.has(edge.to)) {
      hopOf.set(
        edge.to,
        typeof edge.hop === "number"
          ? edge.hop + 1
          : 1,
      );
    }
  }

  const ids = new Set<string>([
    r.address,
    ...edgesData.flatMap((edge) => [
      edge.from,
      edge.to,
    ]),
  ]);

  const nodes: GraphNode[] = [...ids].map((id) => {
    const tag = tagsData[id];

    const type: EntityType =
      id === r.address
        ? "reported"
        : ((tag?.entity_type as EntityType) ??
          "unknown");

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
    };
  });

  const edges: GraphEdge[] = edgesData.map(
    (edge) => ({
      ...edge,
      is_spoofed_token:
        !!edge.is_spoofed_token,
    }),
  );

  const timestamp = Math.floor(
    Date.now() / 1000,
  );

  const workspace: Workspace = {
    id: r.workspace_id,
    traceId: r.trace_id,

    title: `Live trace – ${r.address.slice(
      0,
      10,
    )}…`,

    complaintId:
      complaintId ??
      `NCRP/2026/LIVE/${String(
        r.trace_id,
      ).padStart(6, "0")}`,

    source: "NCRP/SAHYOG",

    victimState: "—",

    address: r.address,

    chain:
      summary.chain ??
      CHAIN_NAMES[chainId] ??
      `Chain ${chainId}`,

    status: "Tracing",

    riskScore,

    riskLevel: levelFromScore(riskScore),

    amountInr: 0,

    createdAt: timestamp,

    members: [ME],

    lead: ME,

    nodes,

    edges,

    reasons: r.risk?.reasons ?? [],

    summary: {
      transactions:
        summary.transactions_analyzed ?? 0,

      counterparties:
        summary.unique_counterparties ?? 0,

      depth:
        summary.max_trace_depth ?? 0,

      assets:
        summary.assets_observed ?? [],

      vasps: arr(entityFindings.vasp),

      bridges: arr(entityFindings.bridge),

      mixers: arr(entityFindings.mixer),

      spoofed: arr(
        summary.spoofed_tokens_detected,
      ),

      crossChain: arr(
        summary.cross_chain_activity,
      ),
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
  };

  const alert: Alert | undefined =
    r.alert_raised
      ? {
          id: `AL-${r.trace_id}`,
          workspaceId: r.workspace_id,
          address: r.address,
          level: workspace.riskLevel,
          message: r.alert_raised
            .replace(
              /^ALERT\s*\[[^\]]+\]\s*/,
              "",
            )
            .trim(),
          at: timestamp,
          acknowledged: false,
        }
      : undefined;

  return {
    ws: workspace,
    alert,
  };
}

export async function runTrace(
  address: string,
  chainId = 1,
  maxHops = 3,
  idempotencyKey?: string,
): Promise<{
  ws: Workspace;
  alert?: Alert;
  source: "live";
}> {
  const safeAddress =
    requireAddress(address);

  const params = new URLSearchParams({
    address: safeAddress,
    chain_id: String(chainId),
    max_hops: String(maxHops),
    check_cross_chain: "true",
  });

  const key =
    idempotencyKey ??
    (typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random()
          .toString(36)
          .slice(2)}`);

  const res = await fetch(
    `${API_URL}/trace?${params.toString()}`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": key,
      },

      cache: "no-store",
    },
  );

  const data = await res
    .json()
    .catch(() => null);

  if (!res.ok) {
    const detail = data?.detail;

    if (
      res.status === 409 &&
      typeof detail === "object" &&
      detail?.message
    ) {
      throw new Error(
        `${detail.message}${
          detail.trace_id
            ? ` Trace ID: ${detail.trace_id}.`
            : ""
        }`,
      );
    }

    throw new Error(
      typeof detail === "string"
        ? detail
        : typeof data?.message === "string"
          ? data.message
          : `Trace failed with HTTP ${res.status}`,
    );
  }

  if (
    !data ||
    typeof data.trace_id !== "number" ||
    !data.workspace_id
  ) {
    throw new Error(
      "Trace completed but the backend returned an invalid trace response.",
    );
  }

  const ws = await getWorkspace(
    String(data.workspace_id),
  );

  let alert: Alert | undefined;

  try {
    const alerts = await getAlerts(500);

    alert = alerts.find(
      (item) =>
        item.workspaceId === ws.id ||
        (item.address &&
          ws.address &&
          item.address.toLowerCase() ===
            ws.address.toLowerCase()),
    );
  } catch {
    // Alert loading should not invalidate
    // an otherwise successful trace.
  }

  return {
    ws,
    alert,
    source: "live",
  };
}

export async function getWorkspaces(
  limit = 100,
): Promise<Workspace[]> {
  return request<Workspace[]>(
    `/workspaces?limit=${limit}`,
  );
}

export async function getWorkspace(
  workspaceId: string,
): Promise<Workspace> {
  const id =
    requireWorkspaceId(workspaceId);

  return request<Workspace>(
    `/workspaces/${encodeURIComponent(id)}`,
  );
}

export async function getAlerts(
  limit = 50,
): Promise<Alert[]> {
  return request<Alert[]>(
    `/alerts?limit=${limit}`,
  );
}

export async function getMembers() {
  return request<typeof MEMBERS>("/members");
}

export async function updateStatus(
  workspaceId: string,
  status: string,
  actor = ME,
): Promise<Workspace> {
  const id =
    requireWorkspaceId(workspaceId);

  return request<Workspace>(
    `/workspaces/${encodeURIComponent(id)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({
        status,
        actor,
      }),
    },
  );
}

export async function addComment(
  workspaceId: string,
  text: string,
  actor = ME,
): Promise<Workspace> {
  const id =
    requireWorkspaceId(workspaceId);

  return request<Workspace>(
    `/workspaces/${encodeURIComponent(id)}/comments`,
    {
      method: "POST",
      body: JSON.stringify({
        text,
        actor,
      }),
    },
  );
}

export async function addTask(
  workspaceId: string,
  text: string,
  assignee = ME,
  actor = ME,
): Promise<Workspace> {
  const id =
    requireWorkspaceId(workspaceId);

  return request<Workspace>(
    `/workspaces/${encodeURIComponent(id)}/tasks`,
    {
      method: "POST",
      body: JSON.stringify({
        text,
        assignee,
        actor,
      }),
    },
  );
}

export async function toggleTask(
  workspaceId: string,
  taskId: string,
  actor = ME,
): Promise<Workspace> {
  const id =
    requireWorkspaceId(workspaceId);

  return request<Workspace>(
    `/workspaces/${encodeURIComponent(
      id,
    )}/tasks/${encodeURIComponent(
      taskId,
    )}?actor=${encodeURIComponent(actor)}`,
    {
      method: "PATCH",
    },
  );
}

export async function inviteMember(
  workspaceId: string,
  memberId: string,
  actor = ME,
): Promise<Workspace> {
  const id =
    requireWorkspaceId(workspaceId);

  return request<Workspace>(
    `/workspaces/${encodeURIComponent(id)}/members`,
    {
      method: "POST",
      body: JSON.stringify({
        member_id: memberId,
        actor,
      }),
    },
  );
}

export async function acknowledgeAlert(
  alertId: string,
): Promise<{
  ok: boolean;
  alert_id: string;
}> {
  if (
    typeof alertId !== "string" ||
    !alertId.trim()
  ) {
    throw new Error("Invalid alert ID.");
  }

  return request<{
    ok: boolean;
    alert_id: string;
  }>(
    `/alerts/${encodeURIComponent(
      alertId,
    )}/ack`,
    {
      method: "PATCH",
    },
  );
}

export async function flagNode(
  workspaceId: string,
  address: string,
  actor = ME,
): Promise<{
  flagged: boolean;
  workspace: Workspace;
}> {
  const id =
    requireWorkspaceId(workspaceId);

  const nodeAddress =
    requireAddress(address);

  return request<{
    flagged: boolean;
    workspace: Workspace;
  }>(
    `/workspaces/${encodeURIComponent(
      id,
    )}/nodes/${encodeURIComponent(
      nodeAddress,
    )}/flag?actor=${encodeURIComponent(actor)}`,
    {
      method: "POST",
    },
  );
}

export async function addNodeNote(
  workspaceId: string,
  address: string,
  text: string,
  actor = ME,
): Promise<Workspace> {
  const id =
    requireWorkspaceId(workspaceId);

  const nodeAddress =
    requireAddress(address);

  if (!text.trim()) {
    throw new Error(
      "Node note cannot be empty.",
    );
  }

  return request<Workspace>(
    `/workspaces/${encodeURIComponent(
      id,
    )}/nodes/${encodeURIComponent(
      nodeAddress,
    )}/notes`,
    {
      method: "POST",
      body: JSON.stringify({
        text: text.trim(),
        actor,
      }),
    },
  );
}

export async function generateReport(
  workspaceId: string,
): Promise<{
  trace_id: number;
  report_url: string;
}> {
  const id =
    requireWorkspaceId(workspaceId);

  const result = await request<{
    trace_id: number;
    report_url: string;
  }>(
    `/workspaces/${encodeURIComponent(
      id,
    )}/report`,
    {
      method: "POST",
    },
  );

  if (
    typeof result?.trace_id !== "number" ||
    !Number.isFinite(result.trace_id)
  ) {
    throw new Error(
      "Report generation completed but no valid trace ID was returned.",
    );
  }

  return result;
}

export function getReportUrl(
  traceId: number,
): string {
  const id = requireTraceId(traceId);

  return `${API_URL}/report/${id}`;
}

export function getEvidenceUrl(
  traceId: number,
): string {
  const id = requireTraceId(traceId);

  return `${API_URL}/evidence/${id}`;
}

export function getGraphUrl(
  traceId: number,
): string {
  const id = requireTraceId(traceId);

  return `${API_URL}/graph/${id}`;
}

export async function getTraceGraph(
  traceId: number,
): Promise<string> {
  const id = requireTraceId(traceId);

  const res = await fetch(
    `${API_URL}/graph/${id}`,
    {
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const error =
      await getErrorMessage(res);

    throw new Error(
      `Failed to load graph (${res.status})${
        error ? `: ${error}` : ""
      }`,
    );
  }

  return res.text();
}

export async function getEvidence(
  traceId: number,
): Promise<unknown> {
  const id = requireTraceId(traceId);

  const res = await fetch(
    `${API_URL}/evidence/${id}`,
    {
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const error =
      await getErrorMessage(res);

    throw new Error(
      `Failed to load evidence (${res.status})${
        error ? `: ${error}` : ""
      }`,
    );
  }

  return res.json();
}

export async function verifyEvidence(
  traceId: number,
): Promise<{
  exists: boolean;
  valid?: boolean;
  hash?: string;
  message?: string;
  [key: string]: unknown;
}> {
  const id = requireTraceId(traceId);

  return request(
    `/evidence/${id}/verify`,
  );
}

export async function getReport(
  traceId: number,
): Promise<Blob> {
  const id = requireTraceId(traceId);

  const res = await fetch(
    `${API_URL}/report/${id}`,
    {
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const error =
      await getErrorMessage(res);

    throw new Error(
      `Failed to load report (${res.status})${
        error ? `: ${error}` : ""
      }`,
    );
  }

  const contentType =
    res.headers.get("content-type") ?? "";

  if (
    !contentType.includes("application/pdf") &&
    !contentType.includes(
      "application/octet-stream",
    )
  ) {
    const text = await res
      .text()
      .catch(() => "");

    throw new Error(
      `Report endpoint returned an unexpected response${
        text ? `: ${text.slice(0, 300)}` : "."
      }`,
    );
  }

  const blob = await res.blob();

  if (blob.size === 0) {
    throw new Error(
      "Report endpoint returned an empty file.",
    );
  }

  return blob;
}

export interface ReportRecord {
  trace_id: number;
  address: string;
  chain_id: number;
  risk: {
    score: number;
    level: string;
  };
  created_at: number;
}

export async function getReports(
  limit = 100,
): Promise<ReportRecord[]> {
  const data =
    await request<ReportRecord[]>(
      `/reports?limit=${limit}`,
    );

  if (!Array.isArray(data)) {
    return [];
  }

  return data.filter(
    (report) =>
      report &&
      typeof report.trace_id === "number",
  );
}

export async function getTraces(
  limit = 50,
) {
  return request(
    `/traces?limit=${limit}`,
  );
}

export async function getDashboardStats(
  days = 30,
) {
  return request(
    `/dashboard/stats?days=${days}`,
  );
}

export { MEMBERS };