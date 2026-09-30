"use client"

import * as React from "react"
import Link from "next/link"
import { toast } from "sonner"
import {
  BellRingIcon, CheckCircle2Icon, CopyIcon, DownloadIcon, FileTextIcon, FlagIcon, GitBranchIcon, HashIcon, ListChecksIcon,
  MessageSquareIcon, PlusIcon, SendIcon, ShieldAlertIcon, SnowflakeIcon, UserPlusIcon, UsersIcon,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { MemberAvatar, MemberStack, Mono, RiskBadge, StatusBadge, memberOf } from "@/components/custom/bits"
import { ENTITY_COLOR, ENTITY_NAME, TxGraph } from "@/components/custom/tx-graph"
import { API_URL } from "@/lib/api"
import { fmtTime, inr, short } from "@/lib/format"
import { MEMBERS, ME } from "@/lib/mock-data"
import { useStore } from "@/lib/store"
import type { CaseStatus } from "@/lib/types"
import { cn } from "@/lib/utils"

const STATUSES: CaseStatus[] = ["New", "Tracing", "In Review", "Freeze Requested", "Closed"]

export default function WorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params)
  const { state, dispatch, ready } = useStore()
  const ws = state.workspaces.find((w) => w.id === id)
  const [inviteOpen, setInviteOpen] = React.useState(false)

  if (!ws) {
    return (
      <Card><CardContent className="py-16 text-center text-muted-foreground">
        {ready ? <>Workspace <b>{id}</b> not found. <Link href="/workspaces" className="underline">Back to workspaces</Link></> : "Loading…"}
      </CardContent></Card>
    )
  }
  const alerts = state.alerts.filter((a) => a.workspaceId === ws.id)
  const copy = (t: string) => { navigator.clipboard?.writeText(t); toast.success("Copied to clipboard") }

  return (
    <>
      {/* ---------- case header ---------- */}
      <Card className="border-cyan-400/[0.14] bg-[linear-gradient(145deg,rgba(10,26,48,0.78),rgba(3,11,23,0.88))] shadow-[0_16px_40px_rgba(0,0,0,0.4)]">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={ws.riskLevel} score={ws.riskScore} />
            <StatusBadge status={ws.status} />
            <Badge variant="outline" className="border-cyan-400/25 bg-cyan-500/10 text-cyan-300 text-[11px]">
              {ws.chain}
            </Badge>
            {ws.traceId && (
              <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300 shadow-[0_0_8px_rgba(16,185,129,0.15)] text-[11px]">
                Live trace #{ws.traceId}
              </Badge>
            )}
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight text-slate-100">{ws.title}</CardTitle>
          <CardDescription className="flex flex-wrap items-center gap-x-4 gap-y-1 text-slate-400 text-xs">
            <span className="font-mono text-cyan-400/80 font-medium">{ws.id}</span>
            <span>{ws.complaintId}</span>
            <span>{ws.victimState}</span>
            <span>Opened {fmtTime(ws.createdAt)}</span>
            <button
              className="inline-flex items-center gap-1.5 rounded border border-cyan-400/20 bg-slate-900/60 px-2 py-0.5 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200 transition-colors"
              onClick={() => copy(ws.address)}
            >
              <Mono>{short(ws.address, 10, 8)}</Mono>
              <CopyIcon className="size-3 text-cyan-400/70" />
            </button>
          </CardDescription>
          <CardAction className="flex flex-wrap items-center gap-2">
            <MemberStack ids={ws.members} />
            <Button
              size="sm"
              variant="outline"
              onClick={() => setInviteOpen(true)}
              className="border-cyan-400/20 bg-slate-900/40 text-slate-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200"
            >
              <UserPlusIcon className="size-3.5" />
              Invite
            </Button>
            <Select
              value={ws.status}
              onValueChange={(v) => v && dispatch({ type: "status", id: ws.id, status: v as CaseStatus })}
            >
              <SelectTrigger size="sm" className="w-40 border-cyan-400/20 bg-slate-900/60 text-slate-200 hover:border-cyan-400/40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-cyan-400/20 bg-[#081224]/95 text-slate-200 backdrop-blur-2xl">
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s} className="focus:bg-cyan-500/10 focus:text-cyan-200">
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              variant="destructive"
              disabled={ws.status === "Freeze Requested" || ws.status === "Closed"}
              className="border border-rose-500/40 bg-gradient-to-r from-rose-600 to-red-600 text-white shadow-[0_0_20px_rgba(244,63,94,0.25)] hover:from-rose-500 hover:to-red-500"
              onClick={() => {
                dispatch({ type: "status", id: ws.id, status: "Freeze Requested" });
                toast.success("Freeze / preservation request drafted", {
                  description: `Sent to compliance desks: ${ws.summary.vasps.join(", ") || "no VASP attributed"}`,
                });
              }}
            >
              <SnowflakeIcon className="size-3.5" />
              Request freeze
            </Button>
          </CardAction>
        </CardHeader>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList className="h-10 w-full justify-start rounded-xl border border-cyan-400/15 bg-slate-950/60 p-1 backdrop-blur-xl sm:w-fit">
          <TabsTrigger
            value="overview"
            className="gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium text-slate-400 transition-all hover:text-slate-200 data-[state=active]:border data-[state=active]:border-cyan-400/30 data-[state=active]:bg-cyan-500/15 data-[state=active]:text-cyan-200 data-[state=active]:shadow-[inset_0_0_12px_rgba(6,182,212,0.15)]"
          >
            <ShieldAlertIcon className="size-3.5" />
            Overview
          </TabsTrigger>
          <TabsTrigger
            value="graph"
            className="gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium text-slate-400 transition-all hover:text-slate-200 data-[state=active]:border data-[state=active]:border-cyan-400/30 data-[state=active]:bg-cyan-500/15 data-[state=active]:text-cyan-200 data-[state=active]:shadow-[inset_0_0_12px_rgba(6,182,212,0.15)]"
          >
            <GitBranchIcon className="size-3.5" />
            Graph
          </TabsTrigger>
          <TabsTrigger
            value="alerts"
            className="gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium text-slate-400 transition-all hover:text-slate-200 data-[state=active]:border data-[state=active]:border-cyan-400/30 data-[state=active]:bg-cyan-500/15 data-[state=active]:text-cyan-200 data-[state=active]:shadow-[inset_0_0_12px_rgba(6,182,212,0.15)]"
          >
            <BellRingIcon className="size-3.5" />
            Alerts
            {alerts.length > 0 && (
              <Badge variant="secondary" className="ml-1 border border-rose-500/30 bg-rose-500/15 px-1.5 py-0 text-[10px] text-rose-300">
                {alerts.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="reports"
            className="gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium text-slate-400 transition-all hover:text-slate-200 data-[state=active]:border data-[state=active]:border-cyan-400/30 data-[state=active]:bg-cyan-500/15 data-[state=active]:text-cyan-200 data-[state=active]:shadow-[inset_0_0_12px_rgba(6,182,212,0.15)]"
          >
            <FileTextIcon className="size-3.5" />
            Reports
          </TabsTrigger>
          <TabsTrigger
            value="team"
            className="gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium text-slate-400 transition-all hover:text-slate-200 data-[state=active]:border data-[state=active]:border-cyan-400/30 data-[state=active]:bg-cyan-500/15 data-[state=active]:text-cyan-200 data-[state=active]:shadow-[inset_0_0_12px_rgba(6,182,212,0.15)]"
          >
            <UsersIcon className="size-3.5" />
            Team
            <Badge variant="secondary" className="ml-1 border border-cyan-400/20 bg-cyan-500/15 px-1.5 py-0 text-[10px] text-cyan-300">
              {ws.comments.length}
            </Badge>
          </TabsTrigger>
        </TabsList>

        {/* ---------- overview ---------- */}
        <TabsContent value="overview" className="mt-4 grid gap-4 @4xl/main:grid-cols-3">
          <Card className="border-cyan-400/[0.12]">
            <CardHeader>
              <CardDescription className="text-xs uppercase tracking-[0.08em] text-slate-400">
                Rule-based risk score
              </CardDescription>
              <CardTitle className="font-mono text-5xl font-extrabold tabular-nums text-slate-100">
                {ws.riskScore}
                <span className="text-xl text-slate-500"> / 100</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="h-2.5 overflow-hidden rounded-full bg-slate-900/80 border border-white/5">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    ws.riskScore >= 75
                      ? "bg-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.6)]"
                      : ws.riskScore >= 50
                      ? "bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.6)]"
                      : ws.riskScore >= 25
                      ? "bg-yellow-500 shadow-[0_0_12px_rgba(234,179,8,0.5)]"
                      : "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.5)]",
                  )}
                  style={{ width: `${ws.riskScore}%` }}
                />
              </div>
              <ul className="space-y-2 text-sm">
                {ws.reasons.length === 0 && <li className="text-slate-500">No risk indicators triggered.</li>}
                {ws.reasons.map((r) => {
                  const m = r.match(/^(\+\d+)\s(.*)$/);
                  return (
                    <li key={r} className="flex items-start gap-2.5 text-xs text-slate-300">
                      <Badge
                        variant="outline"
                        className="shrink-0 font-mono text-[11px] font-semibold border-cyan-400/25 bg-cyan-500/10 text-cyan-300 tabular-nums"
                      >
                        {m?.[1] ?? "•"}
                      </Badge>
                      <span className="leading-snug pt-0.5">{m?.[2] ?? r}</span>
                    </li>
                  );
                })}
              </ul>
            </CardContent>
          </Card>

          <div className="grid gap-4 @4xl/main:col-span-2">
            <div className="grid grid-cols-2 gap-4 @2xl/main:grid-cols-4">
              {[
                ["Transactions", ws.summary.transactions],
                ["Counterparties", ws.summary.counterparties],
                ["Trace depth", `${ws.summary.depth} hops`],
                ["Est. value", ws.amountInr ? inr(ws.amountInr) : "—"],
              ].map(([l, v]) => (
                <Card key={l as string} className="py-3.5 border-cyan-400/[0.12] bg-[linear-gradient(145deg,rgba(10,26,48,0.72),rgba(3,11,23,0.85))]">
                  <CardHeader className="gap-1 pb-0">
                    <CardDescription className="text-[10px] font-medium uppercase tracking-[0.12em] text-cyan-400/70">
                      {l}
                    </CardDescription>
                    <CardTitle className="font-mono text-2xl font-bold tabular-nums text-slate-100">
                      {v}
                    </CardTitle>
                  </CardHeader>
                </Card>
              ))}
            </div>
            <Card className="border-cyan-400/[0.12]">
              <CardHeader>
                <CardTitle className="text-slate-100">Attributed entities</CardTitle>
                <CardDescription className="text-slate-400">
                  Addresses matched against the labelled VASP / bridge / mixer dataset
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader className="border-cyan-400/[0.12]">
                    <TableRow className="border-cyan-400/[0.08] hover:bg-transparent">
                      <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Entity</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Type</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Address</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Hop</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Confidence</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ws.nodes
                      .filter((n) => n.type !== "unknown" && n.type !== "reported")
                      .map((n) => (
                        <TableRow key={n.id} className="border-cyan-400/[0.08] hover:bg-cyan-500/[0.04]">
                          <TableCell className="font-medium text-slate-200">{n.label}</TableCell>
                          <TableCell>
                            <span className="inline-flex items-center gap-1.5 text-xs text-slate-300">
                              <i className="size-2 rounded-full shadow-[0_0_6px_currentColor]" style={{ background: ENTITY_COLOR[n.type], color: ENTITY_COLOR[n.type] }} />
                              {ENTITY_NAME[n.type]}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Mono>{short(n.id, 8, 6)}</Mono>
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">{n.hop}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="border-cyan-400/25 bg-cyan-500/10 text-cyan-300 font-mono text-[11px]">
                              {n.confidence}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    {!ws.nodes.some((n) => n.type !== "unknown" && n.type !== "reported") && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-slate-500 py-6">
                          No known entities reached yet.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
            <Card className="border-cyan-400/[0.12]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-slate-100">
                  <HashIcon className="size-4 text-cyan-400" />
                  Evidence integrity
                </CardTitle>
                <CardDescription className="text-slate-400">
                  SHA-256 over raw blockchain records + derived edges — tamper-evident for court submission
                </CardDescription>
              </CardHeader>
              <CardContent className="flex items-center gap-2">
                <div className="flex-1 rounded-lg border border-cyan-400/15 bg-slate-950/60 p-2.5">
                  <Mono className="break-all text-cyan-300">
                    {ws.evidenceHash || "Generated when the trace is saved on the backend"}
                  </Mono>
                </div>
                {ws.evidenceHash && (
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    className="border border-cyan-400/20 bg-slate-900/40 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200"
                    onClick={() => copy(ws.evidenceHash)}
                  >
                    <CopyIcon className="size-4" />
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ---------- graph ---------- */}
        <TabsContent value="graph" className="mt-4">
          <GraphTab wsId={ws.id} />
        </TabsContent>

        {/* ---------- alerts ---------- */}
        <TabsContent value="alerts" className="mt-4">
          <Card className="border-cyan-400/[0.12]">
            <CardHeader>
              <CardTitle className="text-slate-100">Case alerts</CardTitle>
              <CardDescription className="text-slate-400">
                Raised automatically when a trace scores High or Critical
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col divide-y divide-cyan-400/[0.08]">
              {alerts.length === 0 && <p className="py-6 text-center text-slate-500">No alerts for this case.</p>}
              {alerts.map((a) => (
                <div key={a.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                  <RiskBadge level={a.level} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-200">{a.message}</p>
                    <p className="text-xs text-slate-500 font-mono">
                      {a.id} · {fmtTime(a.at)}
                    </p>
                  </div>
                  {a.acknowledged ? (
                    <span className="flex items-center gap-1.5 font-mono text-xs text-slate-500">
                      <CheckCircle2Icon className="size-3.5 text-emerald-400" />
                      Acknowledged
                    </span>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-cyan-400/25 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200"
                      onClick={() => dispatch({ type: "ack", alertId: a.id })}
                    >
                      Acknowledge
                    </Button>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------- reports ---------- */}
        <TabsContent value="reports" className="mt-4">
          <Card className="border-cyan-400/[0.12]">
            <CardHeader>
              <CardTitle className="text-slate-100">Reports & evidence</CardTitle>
              <CardDescription className="text-slate-400">
                Court-ready PDF reports and hashed evidence bundles
              </CardDescription>
              <CardAction>
                <Button
                  size="sm"
                  className="gap-1.5 border border-cyan-300/20 bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-[0_0_16px_rgba(6,182,212,0.2)] hover:from-cyan-400 hover:to-blue-500"
                  onClick={() => {
                    dispatch({ type: "genReport", id: ws.id });
                    toast.success("Report generated");
                  }}
                >
                  <PlusIcon className="size-3.5" />
                  Generate report
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent className="flex flex-col divide-y divide-cyan-400/[0.08]">
              {ws.reports.map((r) => (
                <div key={r.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="flex size-9 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-500/10 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.12)]">
                    <FileTextIcon className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-200">{r.name}</p>
                    <p className="text-xs text-slate-500">
                      {memberOf(r.by).name} · {fmtTime(r.at)}
                    </p>
                  </div>
                  <Badge variant="outline" className="border-cyan-400/25 bg-cyan-500/10 text-cyan-300 font-mono text-xs">
                    {r.kind}
                  </Badge>
                  {ws.traceId ? (
                    <a
                      className="inline-flex"
                      href={`${API_URL}/${r.kind === "PDF" ? "report" : "evidence"}/${ws.traceId}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <Button
                        size="sm"
                        variant="outline"
                        nativeButton={false}
                        render={<span />}
                        className="border-cyan-400/20 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200"
                      >
                        <DownloadIcon className="size-3.5" />
                        Open
                      </Button>
                    </a>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-cyan-400/20 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200"
                      onClick={() => toast.info("Demo case – run a live trace to download the real PDF")}
                    >
                      <DownloadIcon className="size-3.5" />
                      Open
                    </Button>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------- team / collaboration ---------- */}
        <TabsContent value="team" className="mt-4">
          <TeamTab wsId={ws.id} onInvite={() => setInviteOpen(true)} />
        </TabsContent>
      </Tabs>

      <Sheet open={inviteOpen} onOpenChange={setInviteOpen}>
        <SheetContent side="right" className="border-cyan-400/20 bg-[#061224]/95 text-slate-200 shadow-2xl backdrop-blur-2xl">
          <SheetHeader>
            <SheetTitle className="text-slate-100">Invite collaborators</SheetTitle>
            <SheetDescription className="text-slate-400">
              Add investigators, forensics, legal and exchange liaisons to this workspace.
            </SheetDescription>
          </SheetHeader>
          <div className="flex flex-col gap-1.5 px-4 pt-2">
            {MEMBERS.map((m) => {
              const inWs = ws.members.includes(m.id);
              return (
                <div
                  key={m.id}
                  className="flex items-center gap-3 rounded-lg border border-transparent p-2.5 transition-colors hover:border-cyan-400/15 hover:bg-cyan-500/[0.06]"
                >
                  <MemberAvatar id={m.id} className="size-9" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-200">{m.name}</p>
                    <p className="truncate text-xs text-slate-400">
                      {m.role} · {m.org}
                    </p>
                  </div>
                  {inWs ? (
                    <Badge variant="outline" className="border-cyan-400/20 bg-cyan-500/10 text-cyan-300 font-mono text-[11px]">
                      Member
                    </Badge>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-cyan-400/25 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200"
                      onClick={() => {
                        dispatch({ type: "invite", id: ws.id, member: m.id });
                        toast.success(`${m.name} invited`);
                      }}
                    >
                      Invite
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}

/* ============================ Graph tab ============================ */
function GraphTab({ wsId }: { wsId: string }) {
  const { state, dispatch } = useStore();
  const ws = state.workspaces.find((w) => w.id === wsId)!;
  const [sel, setSel] = React.useState<string | null>(null);
  const [note, setNote] = React.useState("");
  const node = ws.nodes.find((n) => n.id === sel);
  const inbound = node ? ws.edges.filter((e) => e.to === node.id) : [];
  const outbound = node ? ws.edges.filter((e) => e.from === node.id) : [];

  return (
    <div className="grid gap-4 @4xl/main:grid-cols-[1fr_320px]">
      <Card className="overflow-hidden border-cyan-400/[0.12]">
        <CardHeader>
          <CardTitle className="text-slate-100">Transaction graph</CardTitle>
          <CardDescription className="text-slate-400 font-mono text-xs">
            {ws.nodes.length} addresses · {ws.edges.length} transfers · left → right = hop distance from reported wallet
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TxGraph nodes={ws.nodes} edges={ws.edges} selected={sel} onSelect={setSel} height={540} />
        </CardContent>
      </Card>

      <Card className="h-fit border-cyan-400/[0.12]">
        <CardHeader>
          <CardTitle className="text-slate-100">{node ? "Node details" : "Select a node"}</CardTitle>
          {!node && (
            <CardDescription className="text-slate-400 text-xs">
              Click any address in the graph to see attribution, flows, and add a note for the team.
            </CardDescription>
          )}
        </CardHeader>
        {node && (
          <CardContent className="space-y-4 text-sm">
            <div>
              <div className="flex items-center gap-2">
                <i className="size-3 rounded-full shadow-[0_0_8px_currentColor]" style={{ background: ENTITY_COLOR[node.type], color: ENTITY_COLOR[node.type] }} />
                <b className="text-slate-100">{node.label}</b>
              </div>
              <Mono className="mt-1 block break-all text-cyan-300/80">{node.id}</Mono>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                ["Hop", node.hop],
                ["In", inbound.length],
                ["Out", outbound.length],
              ].map(([l, v]) => (
                <div key={l as string} className="rounded-lg border border-cyan-400/15 bg-slate-950/60 py-2">
                  <div className="font-mono text-lg font-bold tabular-nums text-slate-100">{v}</div>
                  <div className="text-[10px] font-medium uppercase tracking-[0.1em] text-cyan-400/70">{l}</div>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Badge variant="outline" className="border-cyan-400/25 bg-cyan-500/10 text-cyan-300">
                {ENTITY_NAME[node.type]}
              </Badge>
              {node.confidence && node.confidence !== "n/a" && (
                <Badge variant="outline" className="border-cyan-400/25 bg-cyan-500/10 text-cyan-300 font-mono">
                  {node.confidence}
                </Badge>
              )}
            </div>
            {(node.type === "vasp" || node.type === "mixer" || node.type === "bridge") && (
              <Button
                size="sm"
                variant={node.flagged ? "secondary" : "destructive"}
                className={cn(
                  "w-full gap-1.5",
                  node.flagged
                    ? "border border-cyan-400/25 bg-slate-800 text-slate-200"
                    : "border border-rose-500/40 bg-gradient-to-r from-rose-600 to-red-600 text-white shadow-[0_0_15px_rgba(244,63,94,0.25)] hover:from-rose-500 hover:to-red-500",
                )}
                onClick={() => {
                  dispatch({ type: "flagNode", id: ws.id, node: node.id });
                  toast(node.flagged ? "Flag removed" : "Flagged for freeze request");
                }}
              >
                <FlagIcon className="size-3.5" />
                {node.flagged ? "Remove freeze flag" : "Flag for freeze request"}
              </Button>
            )}
            <div className="space-y-2 border-t border-cyan-400/[0.10] pt-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-cyan-400/70">Team notes</p>
              {(node.notes ?? []).map((n, i) => (
                <div key={i} className="rounded-lg border border-cyan-400/15 bg-slate-950/60 p-2.5 text-xs">
                  <p className="text-slate-200">{n.text}</p>
                  <p className="mt-1 text-[11px] text-slate-500 font-mono">
                    {memberOf(n.by).name} · {fmtTime(n.at)}
                  </p>
                </div>
              ))}
              <div className="flex gap-2">
                <Input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add a note…"
                  className="border-cyan-400/20 bg-slate-950/60 text-slate-200 placeholder:text-slate-500 text-xs"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && note.trim()) {
                      dispatch({ type: "noteNode", id: ws.id, node: node.id, text: note.trim() });
                      setNote("");
                    }
                  }}
                />
                <Button
                  size="icon"
                  variant="outline"
                  disabled={!note.trim()}
                  className="border-cyan-400/25 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200 shrink-0"
                  onClick={() => {
                    dispatch({ type: "noteNode", id: ws.id, node: node.id, text: note.trim() });
                    setNote("");
                  }}
                >
                  <SendIcon className="size-3.5" />
                </Button>
              </div>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}

/* ============================ Team tab ============================ */
function TeamTab({ wsId, onInvite }: { wsId: string; onInvite: () => void }) {
  const { state, dispatch } = useStore();
  const ws = state.workspaces.find((w) => w.id === wsId)!;
  const [text, setText] = React.useState("");
  const [task, setTask] = React.useState("");
  const send = () => {
    if (!text.trim()) return;
    dispatch({ type: "comment", id: ws.id, text: text.trim() });
    setText("");
  };
  const render = (t: string) =>
    t.split(/(@[A-Za-z]+)/g).map((p, i) =>
      p.startsWith("@") ? (
        <span key={i} className="rounded border border-cyan-400/30 bg-cyan-500/15 px-1.5 py-0.5 text-cyan-300 font-mono text-xs">
          {p}
        </span>
      ) : (
        p
      ),
    );

  return (
    <div className="grid gap-4 @4xl/main:grid-cols-[1fr_340px]">
      <Card className="border-cyan-400/[0.12]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100">
            <MessageSquareIcon className="size-4 text-cyan-400" />
            Discussion
          </CardTitle>
          <CardDescription className="text-slate-400">
            Shared thread for everyone on this case. Mention teammates with @name.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex max-h-[380px] flex-col gap-4 overflow-y-auto pr-1">
            {ws.comments.length === 0 && (
              <p className="py-6 text-center text-slate-500">No messages yet. Start the discussion.</p>
            )}
            {ws.comments.map((c) => (
              <div key={c.id} className="flex gap-3">
                <MemberAvatar id={c.by} className="size-8" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-slate-200">
                    <b className="font-semibold text-slate-100">{memberOf(c.by).name}</b>{" "}
                    <span className="text-xs text-slate-500 font-mono">
                      · {memberOf(c.by).role} · {fmtTime(c.at)}
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-slate-300 leading-relaxed">{render(c.text)}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="flex gap-2 border-t border-cyan-400/[0.10] pt-4">
            <MemberAvatar id={ME} className="size-8" />
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Write a comment… (Ctrl+Enter to send)"
              className="min-h-12 border-cyan-400/20 bg-slate-950/60 text-slate-200 placeholder:text-slate-500 text-sm"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send();
              }}
            />
            <Button
              size="icon"
              onClick={send}
              disabled={!text.trim()}
              className="border border-cyan-300/20 bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-[0_0_12px_rgba(6,182,212,0.2)] hover:from-cyan-400 hover:to-blue-500 shrink-0"
            >
              <SendIcon className="size-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-4">
        <Card className="border-cyan-400/[0.12]">
          <CardHeader>
            <CardTitle className="text-slate-100">Members</CardTitle>
            <CardAction>
              <Button
                size="xs"
                variant="outline"
                onClick={onInvite}
                className="gap-1 border-cyan-400/20 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200"
              >
                <UserPlusIcon className="size-3" />
                Invite
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-2.5">
            {ws.members.map((id) => {
              const m = memberOf(id);
              return (
                <div key={id} className="flex items-center gap-2.5">
                  <div className="relative">
                    <MemberAvatar id={id} className="size-8" />
                    <span
                      className={cn(
                        "absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full border-2 border-slate-950",
                        m.online ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" : "bg-slate-600",
                      )}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-200">
                      {m.name}
                      {id === ws.lead && (
                        <span className="ml-1.5 rounded border border-amber-400/30 bg-amber-500/10 px-1 py-0.2 text-[10px] font-mono text-amber-300">
                          Lead
                        </span>
                      )}
                    </p>
                    <p className="truncate text-xs text-slate-400">
                      {m.role} · {m.org}
                    </p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card className="border-cyan-400/[0.12]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-100">
              <ListChecksIcon className="size-4 text-cyan-400" />
              Tasks
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {ws.tasks.map((t) => (
              <label
                key={t.id}
                className="flex cursor-pointer items-start gap-2.5 rounded-lg p-1.5 transition-colors hover:bg-cyan-500/[0.04] text-sm"
              >
                <Checkbox
                  checked={t.done}
                  onCheckedChange={() => dispatch({ type: "toggleTask", id: ws.id, taskId: t.id })}
                  className="mt-0.5 border-cyan-400/30 data-[state=checked]:bg-cyan-500 data-[state=checked]:border-cyan-500"
                />
                <span className={cn("flex-1 text-xs text-slate-300", t.done && "text-slate-500 line-through")}>
                  {t.text}
                </span>
                <MemberAvatar id={t.assignee} className="size-5" />
              </label>
            ))}
            <div className="flex gap-2 pt-2">
              <Input
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="New task…"
                className="border-cyan-400/20 bg-slate-950/60 text-slate-200 placeholder:text-slate-500 text-xs"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && task.trim()) {
                    dispatch({ type: "addTask", id: ws.id, text: task.trim(), assignee: ME });
                    setTask("");
                  }
                }}
              />
              <Button
                size="icon"
                variant="outline"
                disabled={!task.trim()}
                className="border-cyan-400/25 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200 shrink-0"
                onClick={() => {
                  dispatch({ type: "addTask", id: ws.id, text: task.trim(), assignee: ME });
                  setTask("");
                }}
              >
                <PlusIcon className="size-3.5" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-cyan-400/[0.12]">
          <CardHeader>
            <CardTitle className="text-slate-100">Activity</CardTitle>
          </CardHeader>
          <CardContent className="flex max-h-64 flex-col gap-3 overflow-y-auto border-l border-cyan-400/20 pl-4 ml-6">
            {ws.activity.slice(0, 12).map((a) => (
              <div key={a.id} className="relative text-xs">
                <span className="absolute top-1 -left-[21px] size-2 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
                <b className="font-semibold text-slate-200">{memberOf(a.by).name.split(" ").slice(-1)[0]}</b>{" "}
                <span className="text-slate-300">{a.text}</span>
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">{fmtTime(a.at)}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
