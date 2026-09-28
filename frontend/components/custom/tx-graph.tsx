"use client"

import * as React from "react"
import type { EntityType, GraphEdge, GraphNode } from "@/lib/types"
import { short } from "@/lib/format"

export const ENTITY_COLOR: Record<EntityType, string> = {
  reported: "#f5c518",
  vasp: "#ef4444",
  bridge: "#f59e0b",
  mixer: "#a855f7",
  contract: "#94a3b8",
  unknown: "#3b82f6",
}
export const ENTITY_NAME: Record<EntityType, string> = {
  reported: "Reported wallet", vasp: "Exchange / VASP", bridge: "Bridge", mixer: "Mixer", contract: "Contract", unknown: "Unidentified",
}

const COL_W = 230
const ROW_H = 74
const PAD = 70

interface Props {
  nodes: GraphNode[]
  edges: GraphEdge[]
  selected?: string | null
  onSelect?: (id: string | null) => void
  height?: number
}

export function TxGraph({ nodes, edges, selected, onSelect, height = 520 }: Props) {
  const wrap = React.useRef<HTMLDivElement>(null)
  const [view, setView] = React.useState({ x: 0, y: 0, k: 1 })
  const drag = React.useRef<{ x: number; y: number; vx: number; vy: number; moved: boolean } | null>(null)
  const [hover, setHover] = React.useState<string | null>(null)

  // ---- layered layout by hop ----
  const layout = React.useMemo(() => {
    const cols = new Map<number, GraphNode[]>()
    nodes.forEach((n) => cols.set(n.hop, [...(cols.get(n.hop) ?? []), n]))
    const pos = new Map<string, { x: number; y: number }>()
    const maxRows = Math.max(...[...cols.values()].map((c) => c.length))
    const H = Math.max(maxRows * ROW_H, 200)
    ;[...cols.entries()].forEach(([hop, list]) => {
      const total = list.length * ROW_H
      list.forEach((n, i) => pos.set(n.id, { x: PAD + hop * COL_W, y: PAD + (H - total) / 2 + i * ROW_H + ROW_H / 2 - 20 }))
    })
    const W = PAD * 2 + Math.max(...nodes.map((n) => n.hop)) * COL_W + 60
    return { pos, W, H: H + PAD * 2 }
  }, [nodes])

  // fit-to-view on mount / when data changes
  const fit = React.useCallback(() => {
    const w = wrap.current?.clientWidth ?? 800
    const k = Math.min(1, w / layout.W, height / layout.H)
    setView({ k, x: Math.max(0, (w - layout.W * k) / 2), y: Math.max(0, (height - layout.H * k) / 2) })
  }, [layout, height])
  React.useEffect(() => { fit() }, [fit])

  // ---- path highlight: everything upstream of the selected/hovered node ----
  const focus = selected ?? hover
  const upstream = React.useMemo(() => {
    if (!focus) return null
    const nset = new Set<string>([focus]); const eset = new Set<number>()
    let grew = true
    while (grew) {
      grew = false
      edges.forEach((e, i) => { if (nset.has(e.to) && !eset.has(i)) { eset.add(i); if (!nset.has(e.from)) { nset.add(e.from); } grew = true } })
    }
    return { nset, eset }
  }, [focus, edges])

  const maxAmt = Math.max(...edges.map((e) => e.amount), 1)
  const zoom = (f: number) => setView((v) => ({ ...v, k: Math.min(2.5, Math.max(0.3, v.k * f)) }))

  return (
    <div ref={wrap} className="relative overflow-hidden rounded-lg border bg-[radial-gradient(circle_at_1px_1px,oklch(1_0_0/6%)_1px,transparent_0)] [background-size:22px_22px]" style={{ height }}>
      <svg
        width="100%" height={height} className="cursor-grab touch-none select-none active:cursor-grabbing"
        onPointerDown={(e) => { drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false }; (e.currentTarget as Element).setPointerCapture(e.pointerId) }}
        onPointerMove={(e) => {
          const d = drag.current; if (!d) return
          const dx = e.clientX - d.x, dy = e.clientY - d.y
          if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true
          setView((v) => ({ ...v, x: d.vx + dx, y: d.vy + dy }))
        }}
        onPointerUp={() => { if (drag.current && !drag.current.moved) onSelect?.(null); drag.current = null }}
        onWheel={(e) => zoom(e.deltaY < 0 ? 1.1 : 0.9)}
      >
        <defs>
          {(["#5dade2", "#ef4444", "#f5c518"] as const).map((c) => (
            <marker key={c} id={`arr-${c.slice(1)}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill={c} />
            </marker>
          ))}
        </defs>
        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {edges.map((e, i) => {
            const a = layout.pos.get(e.from), b = layout.pos.get(e.to)
            if (!a || !b) return null
            const on = !upstream || upstream.eset.has(i)
            const color = e.is_spoofed_token ? "#ef4444" : upstream?.eset.has(i) ? "#f5c518" : "#5dade2"
            const mx = (a.x + b.x) / 2
            const w = 1.2 + (e.amount / maxAmt) * 4.5
            return (
              <g key={i} opacity={on ? 1 : 0.12}>
                <path d={`M ${a.x + 22} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x - 24} ${b.y}`} fill="none" stroke={color} strokeWidth={w}
                  strokeDasharray={e.is_spoofed_token ? "6 4" : undefined} markerEnd={`url(#arr-${color.slice(1)})`} strokeOpacity={0.85}>
                  <title>{`${e.amount} ${e.token} · ${short(e.tx_hash, 10, 6)}`}</title>
                </path>
                {view.k > 0.6 && (
                  <text x={mx} y={(a.y + b.y) / 2 - 6} textAnchor="middle" className="fill-muted-foreground" fontSize={10}>
                    {e.amount < 0.01 ? e.amount.toExponential(1) : e.amount.toFixed(2)} {e.token}
                  </text>
                )}
              </g>
            )
          })}
          {nodes.map((n) => {
            const p = layout.pos.get(n.id)!
            const on = !upstream || upstream.nset.has(n.id)
            const r = n.type === "reported" ? 22 : n.type === "unknown" ? 15 : 19
            const sel = selected === n.id
            return (
              <g key={n.id} transform={`translate(${p.x} ${p.y})`} opacity={on ? 1 : 0.2} className="cursor-pointer"
                onPointerDown={(e) => e.stopPropagation()}
                onClick={(e) => { e.stopPropagation(); onSelect?.(n.id) }}
                onPointerEnter={() => setHover(n.id)} onPointerLeave={() => setHover(null)}>
                {(n.type === "vasp" || n.flagged) && <circle r={r + 9} fill={ENTITY_COLOR[n.type]} opacity={0.15} />}
                {sel && <circle r={r + 6} fill="none" stroke="#fff" strokeWidth={2} strokeDasharray="4 3" />}
                <circle r={r} fill={ENTITY_COLOR[n.type]} stroke={n.flagged ? "#fff" : "oklch(0.145 0 0)"} strokeWidth={n.flagged ? 3 : 2} />
                {n.flagged && <text textAnchor="middle" dy={4} fontSize={13} fill="#111">⚑</text>}
                <text y={r + 15} textAnchor="middle" className="fill-foreground" fontSize={11} fontWeight={n.type === "unknown" ? 400 : 600}>
                  {n.label === "Unidentified" ? short(n.id, 6, 4) : n.label}
                </text>
                {n.label !== "Unidentified" && (
                  <text y={r + 28} textAnchor="middle" className="fill-muted-foreground" fontSize={9} fontFamily="var(--font-geist-mono)">{short(n.id, 6, 4)}</text>
                )}
              </g>
            )
          })}
        </g>
      </svg>

      {/* legend */}
      <div className="pointer-events-none absolute top-3 left-3 flex flex-wrap gap-x-3 gap-y-1 rounded-md border bg-background/80 px-2.5 py-1.5 text-[11px] backdrop-blur">
        {(Object.keys(ENTITY_COLOR) as EntityType[]).map((t) => (
          <span key={t} className="flex items-center gap-1.5"><i className="size-2.5 rounded-full" style={{ background: ENTITY_COLOR[t] }} />{ENTITY_NAME[t]}</span>
        ))}
        <span className="flex items-center gap-1.5"><i className="h-0 w-4 border-t-2 border-dashed border-red-500" />Spoofed token</span>
      </div>
      {/* controls */}
      <div className="absolute right-3 bottom-3 flex flex-col gap-1">
        {[["+", () => zoom(1.2)], ["−", () => zoom(0.83)], ["⤢", fit]].map(([l, f]) => (
          <button key={l as string} onClick={f as () => void} className="size-7 rounded-md border bg-background/80 text-sm backdrop-blur hover:bg-accent">{l as string}</button>
        ))}
      </div>
      <div className="pointer-events-none absolute bottom-3 left-3 text-[11px] text-muted-foreground">
        Click a node to highlight its funding path · drag to pan · scroll to zoom
      </div>
    </div>
  )
}
