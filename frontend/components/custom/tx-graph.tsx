"use client";

import * as React from "react";
import type { EntityType, GraphEdge, GraphNode } from "@/lib/types";
import { short } from "@/lib/format";

export const ENTITY_COLOR: Record<EntityType, string> = {
  reported: "#f5c518",
  vasp: "#ef4444",
  bridge: "#f59e0b",
  mixer: "#a855f7",
  contract: "#94a3b8",
  unknown: "#3b82f6",
};

export const ENTITY_NAME: Record<EntityType, string> = {
  reported: "Reported wallet",
  vasp: "Exchange / VASP",
  bridge: "Bridge",
  mixer: "Mixer",
  contract: "Contract",
  unknown: "Unidentified wallet",
};

const BEHAVIOR_COLOR = {
  hot: "#38bdf8",
  cold: "#8b5cf6",
  active: "#22c55e",
  unknown: "#64748b",
};

const FLOW_COLOR = "#5dade2";
const FOCUS_COLOR = "#f5c518";
const SPOOF_COLOR = "#ef4444";
const INTERACTION_COLOR = "#64748b";

const COL_W = 260;
const ROW_H = 88;
const PAD = 80;

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  height?: number;
}

type RuntimeNode = GraphNode & {
  behavior?: string;
  behavior_label?: string;
  behavior_confidence?: string;
  wallet_behavior?: string;
  wallet_behavior_label?: string;
  confidence?: string;
  entity_type?: string;
  entity?: string;
  name?: string;
  display_name?: string;
  symbol?: string;
  token_symbol?: string;
  contract_name?: string;
  is_vasp?: boolean;
  is_exchange?: boolean;
  is_bridge?: boolean;
  is_mixer?: boolean;
  incoming_transactions?: number;
  outgoing_transactions?: number;
  incoming_count?: number;
  outgoing_count?: number;
  unique_incoming_counterparties?: number;
  unique_outgoing_counterparties?: number;
  flagged?: boolean;
};

type RuntimeEdge = GraphEdge & {
  flow_kind?: string;
  kind?: string;
  edge_type?: string;
  is_value_transfer?: boolean;
  is_transfer?: boolean;
  is_contract_interaction?: boolean;
  interaction?: boolean;
  method?: string;
  function?: string;
  contract_method?: string;
  asset?: string;
  token_symbol?: string;
  symbol?: string;
  token?: string;
  amount?: number;
  value?: number;
  value_display?: string;
  label?: string;
};

function nodeMeta(node: GraphNode): RuntimeNode {
  return node as RuntimeNode;
}

function edgeMeta(edge: GraphEdge): RuntimeEdge {
  return edge as RuntimeEdge;
}

function normalize(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, "_");
}

function getBehavior(node: GraphNode): {
  key: "hot" | "cold" | "active" | "unknown" | null;
  label: string | null;
  confidence: string | null;
} {
  const n = nodeMeta(node);

  const raw = normalize(
    n.behavior ??
      n.wallet_behavior ??
      n.behavior_label ??
      n.wallet_behavior_label,
  );

  if (
    raw.includes("hot") ||
    raw.includes("hot_wallet") ||
    raw.includes("hotwallet")
  ) {
    return {
      key: "hot",
      label: "Hot-wallet behavior",
      confidence: n.behavior_confidence ?? n.confidence ?? null,
    };
  }

  if (
    raw.includes("cold") ||
    raw.includes("cold_storage") ||
    raw.includes("coldstorage")
  ) {
    return {
      key: "cold",
      label: "Cold-storage behavior",
      confidence: n.behavior_confidence ?? n.confidence ?? null,
    };
  }

  if (
    raw.includes("active") ||
    raw.includes("mixed") ||
    raw.includes("pass_through")
  ) {
    return {
      key: "active",
      label: "Active wallet behavior",
      confidence: n.behavior_confidence ?? n.confidence ?? null,
    };
  }

  if (raw === "hot_wallet_like") {
    return {
      key: "hot",
      label: "Hot-wallet behavior",
      confidence: n.behavior_confidence ?? n.confidence ?? null,
    };
  }

  if (raw === "cold_storage_like") {
    return {
      key: "cold",
      label: "Cold-storage behavior",
      confidence: n.behavior_confidence ?? n.confidence ?? null,
    };
  }

  if (raw === "active_wallet") {
    return {
      key: "active",
      label: "Active wallet behavior",
      confidence: n.behavior_confidence ?? n.confidence ?? null,
    };
  }

  return {
    key: null,
    label: null,
    confidence: null,
  };
}

function getEntityType(node: GraphNode): EntityType {
  const n = nodeMeta(node);
  const raw = normalize(n.entity_type ?? n.entity ?? node.type);

  if (
    raw === "reported" ||
    raw === "reported_wallet" ||
    raw === "suspect" ||
    raw === "victim"
  ) {
    return "reported";
  }

  if (raw === "vasp" || raw === "exchange" || raw === "exchange_vasp") {
    return "vasp";
  }

  if (raw === "bridge") return "bridge";
  if (raw === "mixer") return "mixer";

  if (
    raw === "contract" ||
    raw === "smart_contract" ||
    raw === "token_contract"
  ) {
    return "contract";
  }

  return "unknown";
}

function isTokenContract(node: GraphNode): boolean {
  const n = nodeMeta(node);
  const raw = normalize(n.entity_type ?? n.entity ?? node.type);

  return (
    raw === "token_contract" ||
    raw.includes("token_contract") ||
    raw === "erc20"
  );
}

function nodeBaseColor(node: GraphNode): string {
  return ENTITY_COLOR[getEntityType(node)];
}

function nodeBehaviorColor(node: GraphNode): string | null {
  const behavior = getBehavior(node);
  const entity = getEntityType(node);

  if (!behavior.key) return null;

  if (
    entity === "reported" ||
    entity === "vasp" ||
    entity === "bridge" ||
    entity === "mixer" ||
    entity === "contract"
  ) {
    return null;
  }

  return BEHAVIOR_COLOR[behavior.key];
}

function nodeDisplayName(node: GraphNode): string {
  const n = nodeMeta(node);
  const entity = getEntityType(node);

  if (entity === "reported") {
    return "Victim-reported wallet";
  }

  if (entity === "vasp") {
    return n.display_name ?? n.name ?? n.label ?? "Exchange / VASP";
  }

  if (entity === "bridge") {
    return n.display_name ?? n.name ?? n.label ?? "Bridge";
  }

  if (entity === "mixer") {
    return n.display_name ?? n.name ?? n.label ?? "Mixer";
  }

  if (isTokenContract(node)) {
    const symbol = n.token_symbol ?? n.symbol;

    if (symbol && isReadableTokenSymbol(symbol)) {
      return `${symbol} token contract`;
    }

    return "Token contract";
  }

  if (entity === "contract") {
    return (
      n.display_name ?? n.contract_name ?? n.name ?? n.label ?? "Smart contract"
    );
  }

  if (
    n.label &&
    n.label !== "Unidentified" &&
    n.label !== "Unknown" &&
    n.label !== "Unknown wallet"
  ) {
    return n.label;
  }

  return "Unidentified wallet";
}

function isReadableTokenSymbol(value: unknown): boolean {
  const s = String(value ?? "").trim();

  if (!s || s.length > 18) return false;
  if (/[�]/.test(s)) return false;

  const printable = [...s].filter((c) => c.charCodeAt(0) >= 32).length;

  return printable === s.length;
}

function nodeSubtitle(node: GraphNode): string {
  const behavior = getBehavior(node);

  if (behavior.label) {
    return behavior.label;
  }

  const entity = getEntityType(node);

  if (entity === "contract") {
    return isTokenContract(node)
      ? "Token contract"
      : "Contract interaction target";
  }

  if (entity === "unknown") {
    return "Wallet / entity not identified";
  }

  return ENTITY_NAME[entity];
}

function nodeTitle(node: GraphNode): string {
  const n = nodeMeta(node);
  const behavior = getBehavior(node);
  const entity = getEntityType(node);

  const lines = [
    nodeDisplayName(node),
    `Address: ${node.id}`,
    `Entity: ${ENTITY_NAME[entity]}`,
  ];

  if (behavior.label) {
    lines.push(
      `Behavior: ${behavior.label}${
        behavior.confidence ? ` (${behavior.confidence})` : ""
      }`,
    );
  }

  if (typeof n.incoming_transactions === "number") {
    lines.push(`Incoming transfers: ${n.incoming_transactions}`);
  } else if (typeof n.incoming_count === "number") {
    lines.push(`Incoming transfers: ${n.incoming_count}`);
  }

  if (typeof n.outgoing_transactions === "number") {
    lines.push(`Outgoing transfers: ${n.outgoing_transactions}`);
  } else if (typeof n.outgoing_count === "number") {
    lines.push(`Outgoing transfers: ${n.outgoing_count}`);
  }

  return lines.join("\n");
}

function edgeKind(edge: GraphEdge): "transfer" | "interaction" {
  const e = edgeMeta(edge);
  const raw = normalize(e.flow_kind ?? e.kind ?? e.edge_type);

  if (
    e.is_contract_interaction === true ||
    e.interaction === true ||
    raw === "interaction" ||
    raw === "contract_interaction" ||
    raw === "contract_call" ||
    raw === "call"
  ) {
    return "interaction";
  }

  if (
    e.is_value_transfer === true ||
    e.is_transfer === true ||
    raw === "transfer" ||
    raw === "value_transfer" ||
    raw === "eth_transfer" ||
    raw === "erc20_transfer" ||
    raw === "internal_transfer"
  ) {
    return "transfer";
  }

  return getEdgeAmount(edge) > 0 ? "transfer" : "interaction";
}

function getEdgeAmount(edge: GraphEdge): number {
  const e = edgeMeta(edge);

  for (const value of [e.amount, e.value]) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return Math.abs(value);
    }

    if (typeof value === "string") {
      const parsed = Number(value);

      if (Number.isFinite(parsed)) {
        return Math.abs(parsed);
      }
    }
  }

  return 0;
}

function getEdgeAsset(edge: GraphEdge): string {
  const e = edgeMeta(edge);

  for (const value of [e.asset, e.token_symbol, e.symbol, e.token]) {
    const text = String(value ?? "").trim();

    if (isReadableTokenSymbol(text)) {
      return text;
    }
  }

  return "Unknown asset";
}

function getEdgeMethod(edge: GraphEdge): string | null {
  const e = edgeMeta(edge);

  const method = e.method ?? e.function ?? e.contract_method ?? null;

  if (!method) return null;

  const text = String(method).trim();

  if (!text) return null;

  return text.length > 42 ? `${text.slice(0, 39)}...` : text;
}

function formatAmount(amount: number): string {
  if (!Number.isFinite(amount) || amount <= 0) {
    return "";
  }

  if (amount < 0.000001) {
    return amount.toExponential(2);
  }

  if (amount < 0.01) {
    return amount.toFixed(4);
  }

  if (amount < 1000) {
    return amount.toFixed(2);
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
    notation: "compact",
  }).format(amount);
}

function edgeLabel(edge: GraphEdge): string {
  const kind = edgeKind(edge);

  if (kind === "interaction") {
    const method = getEdgeMethod(edge);

    return method ? `Call · ${method}` : "Contract interaction";
  }

  const amount = getEdgeAmount(edge);
  const asset = getEdgeAsset(edge);

  if (amount <= 0) {
    return asset === "Unknown asset" ? "Value transfer" : asset;
  }

  return `${formatAmount(amount)} ${asset}`;
}

function edgeTitle(edge: GraphEdge): string {
  const kind = edgeKind(edge);
  const e = edgeMeta(edge);

  const lines = [
    kind === "transfer" ? "Observed value transfer" : "Contract interaction",
    `${edge.from} → ${edge.to}`,
  ];

  if (kind === "transfer") {
    const amount = getEdgeAmount(edge);
    const asset = getEdgeAsset(edge);

    if (amount > 0) {
      lines.push(`Amount: ${formatAmount(amount)} ${asset}`);
    } else if (asset !== "Unknown asset") {
      lines.push(`Asset: ${asset}`);
    }
  }

  const method = getEdgeMethod(edge);

  if (kind === "interaction" && method) {
    lines.push(`Method: ${method}`);
  }

  if (e.tx_hash) {
    lines.push(`Tx: ${short(e.tx_hash, 10, 6)}`);
  }

  if (e.is_spoofed_token) {
    lines.push("WARNING: suspected spoofed/lookalike token");
  }

  return lines.join("\n");
}

export function TxGraph({
  nodes,
  edges,
  selected,
  onSelect,
  height = 520,
}: Props) {
  const wrap = React.useRef<HTMLDivElement>(null);

  const [view, setView] = React.useState({
    x: 0,
    y: 0,
    k: 1,
  });

  const drag = React.useRef<{
    x: number;
    y: number;
    vx: number;
    vy: number;
    moved: boolean;
  } | null>(null);

  const [hover, setHover] = React.useState<string | null>(null);

  const renderEdges = React.useMemo(() => {
    const seen = new Set<string>();

    return edges.filter((edge) => {
      const e = edgeMeta(edge);

      const key = [
        edge.from,
        edge.to,
        edgeKind(edge),
        getEdgeAsset(edge),
        getEdgeAmount(edge),
        e.tx_hash ?? "",
        getEdgeMethod(edge) ?? "",
      ].join("|");

      if (seen.has(key)) {
        return false;
      }

      seen.add(key);
      return true;
    });
  }, [edges]);

  const layout = React.useMemo(() => {
    const cols = new Map<number, GraphNode[]>();

    nodes.forEach((node) => {
      const hop =
        typeof node.hop === "number" && Number.isFinite(node.hop)
          ? node.hop
          : 0;

      cols.set(hop, [...(cols.get(hop) ?? []), node]);
    });

    const pos = new Map<string, { x: number; y: number }>();

    const maxRows = Math.max(
      1,
      ...[...cols.values()].map((column) => column.length),
    );

    const H = Math.max(maxRows * ROW_H, 250);

    const sortedColumns = [...cols.entries()].sort(([a], [b]) => a - b);

    sortedColumns.forEach(([hop, list]) => {
      const sorted = [...list].sort((a, b) => a.id.localeCompare(b.id));

      const total = sorted.length * ROW_H;

      sorted.forEach((node, index) => {
        pos.set(node.id, {
          x: PAD + hop * COL_W,
          y: PAD + (H - total) / 2 + index * ROW_H + ROW_H / 2 - 10,
        });
      });
    });

    const maxHop = Math.max(
      0,
      ...nodes.map((node) => (typeof node.hop === "number" ? node.hop : 0)),
    );

    const W = PAD * 2 + maxHop * COL_W + 120;

    return {
      pos,
      W,
      H: H + PAD * 2,
    };
  }, [nodes]);

  const fit = React.useCallback(() => {
    const w = wrap.current?.clientWidth ?? 800;

    const k = Math.min(1, w / layout.W, height / layout.H);

    setView({
      k,
      x: Math.max(0, (w - layout.W * k) / 2),
      y: Math.max(0, (height - layout.H * k) / 2),
    });
  }, [layout, height]);

  React.useEffect(() => {
    fit();
  }, [fit]);

  const focus = selected ?? hover;

  const upstream = React.useMemo(() => {
    if (!focus) return null;

    const nodeSet = new Set<string>([focus]);

    const edgeSet = new Set<number>();

    let grew = true;

    while (grew) {
      grew = false;

      renderEdges.forEach((edge, index) => {
        if (nodeSet.has(edge.to) && !edgeSet.has(index)) {
          edgeSet.add(index);

          if (!nodeSet.has(edge.from)) {
            nodeSet.add(edge.from);
            grew = true;
          }
        }
      });
    }

    return {
      nset: nodeSet,
      eset: edgeSet,
    };
  }, [focus, renderEdges]);

  const maxAmt = Math.max(1, ...renderEdges.map((edge) => getEdgeAmount(edge)));

  const zoom = React.useCallback((factor: number) => {
    setView((current) => ({
      ...current,
      k: Math.min(2.5, Math.max(0.3, current.k * factor)),
    }));
  }, []);

  if (!nodes.length) {
    return (
      <div
        ref={wrap}
        className="relative flex items-center justify-center overflow-hidden rounded-lg border bg-[radial-gradient(circle_at_1px_1px,oklch(1_0_0/6%)_1px,transparent_0)] [background-size:22px_22px]"
        style={{ height }}
      >
        <div className="text-center">
          <div className="text-sm font-medium">No graph data available</div>
          <div className="mt-1 text-xs text-muted-foreground">
            No traceable addresses were returned for this investigation.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={wrap}
      className="relative overflow-hidden rounded-lg border bg-[radial-gradient(circle_at_1px_1px,oklch(1_0_0/6%)_1px,transparent_0)] [background-size:22px_22px]"
      style={{ height }}
    >
      <svg
        width="100%"
        height={height}
        className="cursor-grab touch-none select-none active:cursor-grabbing"
        onPointerDown={(event) => {
          drag.current = {
            x: event.clientX,
            y: event.clientY,
            vx: view.x,
            vy: view.y,
            moved: false,
          };

          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          const current = drag.current;

          if (!current) return;

          const dx = event.clientX - current.x;

          const dy = event.clientY - current.y;

          if (Math.abs(dx) + Math.abs(dy) > 3) {
            current.moved = true;
          }

          setView((previous) => ({
            ...previous,
            x: current.vx + dx,
            y: current.vy + dy,
          }));
        }}
        onPointerUp={() => {
          if (drag.current && !drag.current.moved) {
            onSelect?.(null);
          }

          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
        onWheel={(event) => {
          zoom(event.deltaY < 0 ? 1.1 : 0.9);
        }}
      >
        <defs>
          <marker
            id="arr-transfer"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={FLOW_COLOR} />
          </marker>

          <marker
            id="arr-focus"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={FOCUS_COLOR} />
          </marker>

          <marker
            id="arr-spoof"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={SPOOF_COLOR} />
          </marker>

          <marker
            id="arr-interaction"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={INTERACTION_COLOR} />
          </marker>
        </defs>

        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {renderEdges.map((edge, index) => {
            const from = layout.pos.get(edge.from);

            const to = layout.pos.get(edge.to);

            if (!from || !to) {
              return null;
            }

            const kind = edgeKind(edge);

            const e = edgeMeta(edge);

            const isFocused = upstream?.eset.has(index) ?? false;

            const visible = !upstream || isFocused;

            const amount = getEdgeAmount(edge);

            const interaction = kind === "interaction";

            const baseColor = e.is_spoofed_token
              ? SPOOF_COLOR
              : isFocused
                ? FOCUS_COLOR
                : interaction
                  ? INTERACTION_COLOR
                  : FLOW_COLOR;

            const width = interaction
              ? 1
              : 1.5 + Math.min(4, (amount / maxAmt) * 4);

            const opacity = interaction
              ? visible
                ? 0.42
                : 0.06
              : visible
                ? 0.9
                : 0.08;

            const marker = e.is_spoofed_token
              ? "arr-spoof"
              : isFocused
                ? "arr-focus"
                : interaction
                  ? "arr-interaction"
                  : "arr-transfer";

            const mx = (from.x + to.x) / 2;

            const curveOffset = ((index % 5) - 2) * 12;

            const controlY = (from.y + to.y) / 2 + curveOffset;

            return (
              <g key={`${edge.from}-${edge.to}-${index}`} opacity={opacity}>
                <path
                  d={`
                      M ${from.x + 24} ${from.y}
                      C ${mx} ${from.y},
                        ${mx} ${controlY},
                        ${to.x - 24} ${to.y}
                    `}
                  fill="none"
                  stroke={baseColor}
                  strokeWidth={width}
                  strokeDasharray={
                    e.is_spoofed_token ? "7 5" : interaction ? "3 5" : undefined
                  }
                  markerEnd={`url(#${marker})`}
                  strokeLinecap="round"
                >
                  <title>{edgeTitle(edge)}</title>
                </path>

                {view.k > 0.58 && (
                  <text
                    x={mx}
                    y={controlY - 7}
                    textAnchor="middle"
                    className={
                      interaction ? "fill-muted-foreground" : "fill-foreground"
                    }
                    fontSize={interaction ? 9 : 10}
                    opacity={interaction ? 0.7 : 0.9}
                  >
                    {edgeLabel(edge)}
                  </text>
                )}
              </g>
            );
          })}

          {nodes.map((node) => {
            const position = layout.pos.get(node.id);

            if (!position) {
              return null;
            }

            const entity = getEntityType(node);

            const behavior = getBehavior(node);

            const baseColor = nodeBaseColor(node);

            const behaviorColor = nodeBehaviorColor(node);

            const isOnPath = !upstream || upstream.nset.has(node.id);

            const selectedNode = selected === node.id;

            const radius =
              entity === "reported"
                ? 24
                : entity === "unknown"
                  ? 18
                  : entity === "contract"
                    ? 17
                    : 20;

            return (
              <g
                key={node.id}
                transform={`translate(${position.x} ${position.y})`}
                opacity={isOnPath ? 1 : 0.2}
                className="cursor-pointer"
                onPointerDown={(event) => {
                  event.stopPropagation();
                }}
                onClick={(event) => {
                  event.stopPropagation();
                  onSelect?.(node.id);
                }}
                onPointerEnter={() => {
                  setHover(node.id);
                }}
                onPointerLeave={() => {
                  setHover(null);
                }}
              >
                {behaviorColor && (
                  <circle
                    r={radius + 7}
                    fill="none"
                    stroke={behaviorColor}
                    strokeWidth={3}
                    opacity={0.75}
                    strokeDasharray={
                      behavior.key === "cold" ? "3 4" : undefined
                    }
                  />
                )}

                {(entity === "vasp" || node.flagged) && (
                  <circle
                    r={radius + 10}
                    fill={node.flagged ? "#ffffff" : baseColor}
                    opacity={node.flagged ? 0.1 : 0.15}
                  />
                )}

                {selectedNode && (
                  <circle
                    r={radius + 7}
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth={2}
                    strokeDasharray="4 3"
                  />
                )}

                <circle
                  r={radius}
                  fill={baseColor}
                  stroke={node.flagged ? "#ffffff" : "oklch(0.145 0 0)"}
                  strokeWidth={node.flagged ? 3 : 2}
                />

                {entity === "reported" && (
                  <text
                    textAnchor="middle"
                    dy={5}
                    fontSize={14}
                    fontWeight={700}
                    fill="#111"
                  >
                    R
                  </text>
                )}

                {entity === "contract" && (
                  <text
                    textAnchor="middle"
                    dy={5}
                    fontSize={11}
                    fontWeight={700}
                    fill="#111"
                  >
                    ◇
                  </text>
                )}

                {node.flagged && (
                  <text textAnchor="middle" dy={4} fontSize={13} fill="#111">
                    ⚑
                  </text>
                )}

                <title>{nodeTitle(node)}</title>

                <text
                  y={radius + 17}
                  textAnchor="middle"
                  className="fill-foreground"
                  fontSize={11}
                  fontWeight={entity === "unknown" ? 500 : 650}
                >
                  {nodeDisplayName(node)}
                </text>

                <text
                  y={radius + 31}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  fontSize={9}
                >
                  {nodeSubtitle(node)}
                </text>

                <text
                  y={radius + 44}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  fontSize={8}
                  fontFamily="var(--font-geist-mono)"
                >
                  {short(node.id, 6, 4)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      <div className="pointer-events-none absolute top-3 left-3 max-w-[calc(100%-24px)] rounded-md border bg-background/90 px-3 py-2 text-[11px] backdrop-blur">
        <div className="flex flex-wrap gap-x-3 gap-y-1.5">
          {(Object.keys(ENTITY_COLOR) as EntityType[]).map((type) => (
            <span key={type} className="flex items-center gap-1.5">
              <i
                className="size-2.5 rounded-full"
                style={{
                  background: ENTITY_COLOR[type],
                }}
              />
              {ENTITY_NAME[type]}
            </span>
          ))}

          <span className="flex items-center gap-1.5">
            <i
              className="size-2.5 rounded-full border-2"
              style={{
                borderColor: BEHAVIOR_COLOR.hot,
              }}
            />
            Hot behavior
          </span>

          <span className="flex items-center gap-1.5">
            <i
              className="size-2.5 rounded-full border-2 border-dashed"
              style={{
                borderColor: BEHAVIOR_COLOR.cold,
              }}
            />
            Cold behavior
          </span>
        </div>

        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 border-t pt-1.5 text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <i
              className="h-0 w-4 border-t-2"
              style={{
                borderColor: FLOW_COLOR,
              }}
            />
            Value transfer
          </span>

          <span className="flex items-center gap-1.5">
            <i
              className="h-0 w-4 border-t border-dashed"
              style={{
                borderColor: INTERACTION_COLOR,
              }}
            />
            Contract interaction
          </span>

          <span className="flex items-center gap-1.5">
            <i className="h-0 w-4 border-t-2 border-dashed border-red-500" />
            Spoofed token
          </span>
        </div>
      </div>

      <div className="absolute right-3 bottom-3 flex flex-col gap-1">
        {[
          ["+", () => zoom(1.2)],
          ["−", () => zoom(0.83)],
          ["⤢", fit],
        ].map(([label, action]) => (
          <button
            key={label as string}
            onClick={action as () => void}
            className="size-7 rounded-md border bg-background/80 text-sm backdrop-blur hover:bg-accent"
            type="button"
          >
            {label as string}
          </button>
        ))}
      </div>

      <div className="pointer-events-none absolute bottom-3 left-3 max-w-[70%] text-[11px] text-muted-foreground">
        Click a node to highlight its upstream funding path · solid lines =
        value transfer · dashed lines = contract interaction · drag to pan ·
        scroll to zoom
      </div>
    </div>
  );
}
