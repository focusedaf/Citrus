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
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={ws.riskLevel} score={ws.riskScore} />
            <StatusBadge status={ws.status} />
            <Badge variant="outline">{ws.chain}</Badge>
            {ws.traceId && <Badge variant="outline" className="border-emerald-500/30 text-emerald-400">Live trace #{ws.traceId}</Badge>}
          </div>
          <CardTitle className="text-xl">{ws.title}</CardTitle>
          <CardDescription className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span>{ws.id}</span><span>{ws.complaintId}</span><span>{ws.victimState}</span><span>Opened {fmtTime(ws.createdAt)}</span>
            <button className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => copy(ws.address)}>
              <Mono>{short(ws.address, 10, 8)}</Mono><CopyIcon className="size-3" />
            </button>
          </CardDescription>
          <CardAction className="flex flex-wrap items-center gap-2">
            <MemberStack ids={ws.members} />
            <Button size="sm" variant="outline" onClick={() => setInviteOpen(true)}><UserPlusIcon />Invite</Button>
            <Select value={ws.status} onValueChange={(v) => v && dispatch({ type: "status", id: ws.id, status: v as CaseStatus })}>
              <SelectTrigger size="sm" className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
            <Button size="sm" variant="destructive" disabled={ws.status === "Freeze Requested" || ws.status === "Closed"}
              onClick={() => { dispatch({ type: "status", id: ws.id, status: "Freeze Requested" }); toast.success("Freeze / preservation request drafted", { description: `Sent to compliance desks: ${ws.summary.vasps.join(", ") || "no VASP attributed"}` }) }}>
              <SnowflakeIcon />Request freeze
            </Button>
          </CardAction>
        </CardHeader>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList className="h-9 w-full justify-start overflow-x-auto sm:w-fit">
          <TabsTrigger value="overview" className="px-3"><ShieldAlertIcon />Overview</TabsTrigger>
          <TabsTrigger value="graph" className="px-3"><GitBranchIcon />Graph</TabsTrigger>
          <TabsTrigger value="alerts" className="px-3"><BellRingIcon />Alerts{alerts.length > 0 && <Badge variant="secondary" className="ml-1">{alerts.length}</Badge>}</TabsTrigger>
          <TabsTrigger value="reports" className="px-3"><FileTextIcon />Reports</TabsTrigger>
          <TabsTrigger value="team" className="px-3"><UsersIcon />Team<Badge variant="secondary" className="ml-1">{ws.comments.length}</Badge></TabsTrigger>
        </TabsList>

        {/* ---------- overview ---------- */}
        <TabsContent value="overview" className="mt-2 grid gap-4 @4xl/main:grid-cols-3">
          <Card>
            <CardHeader><CardDescription>Rule-based risk score</CardDescription>
              <CardTitle className="text-5xl font-semibold tabular-nums">{ws.riskScore}<span className="text-xl text-muted-foreground"> / 100</span></CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div className={cn("h-full rounded-full", ws.riskScore >= 75 ? "bg-red-500" : ws.riskScore >= 50 ? "bg-orange-500" : ws.riskScore >= 25 ? "bg-yellow-500" : "bg-emerald-500")} style={{ width: `${ws.riskScore}%` }} />
              </div>
              <ul className="space-y-1.5 text-sm">
                {ws.reasons.length === 0 && <li className="text-muted-foreground">No risk indicators triggered.</li>}
                {ws.reasons.map((r) => {
                  const m = r.match(/^(\+\d+)\s(.*)$/)
                  return <li key={r} className="flex gap-2"><Badge variant="outline" className="shrink-0 tabular-nums">{m?.[1] ?? "•"}</Badge><span>{m?.[2] ?? r}</span></li>
                })}
              </ul>
            </CardContent>
          </Card>

          <div className="grid gap-4 @4xl/main:col-span-2">
            <div className="grid grid-cols-2 gap-4 @2xl/main:grid-cols-4">
              {[
                ["Transactions", ws.summary.transactions], ["Counterparties", ws.summary.counterparties],
                ["Trace depth", `${ws.summary.depth} hops`], ["Est. value", ws.amountInr ? inr(ws.amountInr) : "—"],
              ].map(([l, v]) => (
                <Card key={l as string} className="py-4"><CardHeader className="gap-0"><CardDescription>{l}</CardDescription><CardTitle className="text-2xl tabular-nums">{v}</CardTitle></CardHeader></Card>
              ))}
            </div>
            <Card>
              <CardHeader><CardTitle>Attributed entities</CardTitle><CardDescription>Addresses matched against the labelled VASP / bridge / mixer dataset</CardDescription></CardHeader>
              <CardContent>
                <Table>
                  <TableHeader><TableRow><TableHead>Entity</TableHead><TableHead>Type</TableHead><TableHead>Address</TableHead><TableHead>Hop</TableHead><TableHead>Confidence</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {ws.nodes.filter((n) => n.type !== "unknown" && n.type !== "reported").map((n) => (
                      <TableRow key={n.id}>
                        <TableCell className="font-medium">{n.label}</TableCell>
                        <TableCell><span className="inline-flex items-center gap-1.5"><i className="size-2 rounded-full" style={{ background: ENTITY_COLOR[n.type] }} />{ENTITY_NAME[n.type]}</span></TableCell>
                        <TableCell><Mono>{short(n.id, 8, 6)}</Mono></TableCell>
                        <TableCell>{n.hop}</TableCell>
                        <TableCell><Badge variant="outline">{n.confidence}</Badge></TableCell>
                      </TableRow>
                    ))}
                    {!ws.nodes.some((n) => n.type !== "unknown" && n.type !== "reported") && (
                      <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground">No known entities reached yet.</TableCell></TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><HashIcon className="size-4" />Evidence integrity</CardTitle>
                <CardDescription>SHA-256 over raw blockchain records + derived edges — tamper-evident for court submission</CardDescription></CardHeader>
              <CardContent className="flex items-center gap-2">
                <Mono className="break-all">{ws.evidenceHash || "Generated when the trace is saved on the backend"}</Mono>
                {ws.evidenceHash && <Button size="icon-sm" variant="ghost" onClick={() => copy(ws.evidenceHash)}><CopyIcon /></Button>}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ---------- graph ---------- */}
        <TabsContent value="graph" className="mt-2"><GraphTab wsId={ws.id} /></TabsContent>

        {/* ---------- alerts ---------- */}
        <TabsContent value="alerts" className="mt-2">
          <Card>
            <CardHeader><CardTitle>Case alerts</CardTitle><CardDescription>Raised automatically when a trace scores High or Critical</CardDescription></CardHeader>
            <CardContent className="flex flex-col divide-y">
              {alerts.length === 0 && <p className="py-6 text-center text-muted-foreground">No alerts for this case.</p>}
              {alerts.map((a) => (
                <div key={a.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                  <RiskBadge level={a.level} />
                  <div className="min-w-0 flex-1"><p className="text-sm">{a.message}</p><p className="text-xs text-muted-foreground">{a.id} · {fmtTime(a.at)}</p></div>
                  {a.acknowledged ? <span className="flex items-center gap-1 text-xs text-muted-foreground"><CheckCircle2Icon className="size-3.5" />Acknowledged</span>
                    : <Button size="sm" variant="outline" onClick={() => dispatch({ type: "ack", alertId: a.id })}>Acknowledge</Button>}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------- reports ---------- */}
        <TabsContent value="reports" className="mt-2">
          <Card>
            <CardHeader><CardTitle>Reports & evidence</CardTitle><CardDescription>Court-ready PDF reports and hashed evidence bundles</CardDescription>
              <CardAction><Button size="sm" onClick={() => { dispatch({ type: "genReport", id: ws.id }); toast.success("Report generated") }}><PlusIcon />Generate report</Button></CardAction></CardHeader>
            <CardContent className="flex flex-col divide-y">
              {ws.reports.map((r) => (
                <div key={r.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="flex size-9 items-center justify-center rounded-md bg-muted"><FileTextIcon className="size-4" /></div>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{r.name}</p><p className="text-xs text-muted-foreground">{memberOf(r.by).name} · {fmtTime(r.at)}</p></div>
                  <Badge variant="outline">{r.kind}</Badge>
                  {ws.traceId
                    ? <a className="inline-flex" href={`${API_URL}/${r.kind === "PDF" ? "report" : "evidence"}/${ws.traceId}`} target="_blank" rel="noreferrer"><Button size="sm" variant="outline" nativeButton={false} render={<span />}><DownloadIcon />Open</Button></a>
                    : <Button size="sm" variant="outline" onClick={() => toast.info("Demo case – run a live trace to download the real PDF")}><DownloadIcon />Open</Button>}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------- team / collaboration ---------- */}
        <TabsContent value="team" className="mt-2"><TeamTab wsId={ws.id} onInvite={() => setInviteOpen(true)} /></TabsContent>
      </Tabs>

      <Sheet open={inviteOpen} onOpenChange={setInviteOpen}>
        <SheetContent side="right">
          <SheetHeader><SheetTitle>Invite collaborators</SheetTitle><SheetDescription>Add investigators, forensics, legal and exchange liaisons to this workspace.</SheetDescription></SheetHeader>
          <div className="flex flex-col gap-1 px-4">
            {MEMBERS.map((m) => {
              const inWs = ws.members.includes(m.id)
              return (
                <div key={m.id} className="flex items-center gap-3 rounded-md p-2 hover:bg-accent/50">
                  <MemberAvatar id={m.id} className="size-9" />
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{m.name}</p><p className="truncate text-xs text-muted-foreground">{m.role} · {m.org}</p></div>
                  {inWs ? <Badge variant="secondary">Member</Badge>
                    : <Button size="sm" variant="outline" onClick={() => { dispatch({ type: "invite", id: ws.id, member: m.id }); toast.success(`${m.name} invited`) }}>Invite</Button>}
                </div>
              )
            })}
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}

/* ============================ Graph tab ============================ */
function GraphTab({ wsId }: { wsId: string }) {
  const { state, dispatch } = useStore()
  const ws = state.workspaces.find((w) => w.id === wsId)!
  const [sel, setSel] = React.useState<string | null>(null)
  const [note, setNote] = React.useState("")
  const node = ws.nodes.find((n) => n.id === sel)
  const inbound = node ? ws.edges.filter((e) => e.to === node.id) : []
  const outbound = node ? ws.edges.filter((e) => e.from === node.id) : []

  return (
    <div className="grid gap-4 @4xl/main:grid-cols-[1fr_320px]">
      <Card className="overflow-hidden">
        <CardHeader><CardTitle>Transaction graph</CardTitle>
          <CardDescription>{ws.nodes.length} addresses · {ws.edges.length} transfers · left → right = hop distance from the reported wallet</CardDescription></CardHeader>
        <CardContent><TxGraph nodes={ws.nodes} edges={ws.edges} selected={sel} onSelect={setSel} height={540} /></CardContent>
      </Card>

      <Card className="h-fit">
        <CardHeader><CardTitle>{node ? "Node details" : "Select a node"}</CardTitle>
          {!node && <CardDescription>Click any address in the graph to see attribution, flows, and add a note for the team.</CardDescription>}</CardHeader>
        {node && (
          <CardContent className="space-y-4 text-sm">
            <div>
              <div className="flex items-center gap-2"><i className="size-3 rounded-full" style={{ background: ENTITY_COLOR[node.type] }} /><b>{node.label}</b></div>
              <Mono className="mt-1 block break-all text-muted-foreground">{node.id}</Mono>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              {[["Hop", node.hop], ["In", inbound.length], ["Out", outbound.length]].map(([l, v]) => (
                <div key={l as string} className="rounded-md border py-1.5"><div className="text-lg font-semibold tabular-nums">{v}</div><div className="text-[11px] text-muted-foreground">{l}</div></div>
              ))}
            </div>
            <div className="flex gap-2">
              <Badge variant="outline">{ENTITY_NAME[node.type]}</Badge>
              {node.confidence && node.confidence !== "n/a" && <Badge variant="outline">{node.confidence}</Badge>}
            </div>
            {(node.type === "vasp" || node.type === "mixer" || node.type === "bridge") && (
              <Button size="sm" variant={node.flagged ? "secondary" : "destructive"} className="w-full"
                onClick={() => { dispatch({ type: "flagNode", id: ws.id, node: node.id }); toast(node.flagged ? "Flag removed" : "Flagged for freeze request") }}>
                <FlagIcon />{node.flagged ? "Remove freeze flag" : "Flag for freeze request"}
              </Button>
            )}
            <div className="space-y-2 border-t pt-3">
              <p className="text-xs font-medium text-muted-foreground">Team notes</p>
              {(node.notes ?? []).map((n, i) => (
                <div key={i} className="rounded-md bg-muted/50 p-2"><p>{n.text}</p><p className="mt-1 text-[11px] text-muted-foreground">{memberOf(n.by).name} · {fmtTime(n.at)}</p></div>
              ))}
              <div className="flex gap-2">
                <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a note…" onKeyDown={(e) => { if (e.key === "Enter" && note.trim()) { dispatch({ type: "noteNode", id: ws.id, node: node.id, text: note.trim() }); setNote("") } }} />
                <Button size="icon" variant="outline" disabled={!note.trim()} onClick={() => { dispatch({ type: "noteNode", id: ws.id, node: node.id, text: note.trim() }); setNote("") }}><SendIcon /></Button>
              </div>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  )
}

/* ============================ Team tab ============================ */
function TeamTab({ wsId, onInvite }: { wsId: string; onInvite: () => void }) {
  const { state, dispatch } = useStore()
  const ws = state.workspaces.find((w) => w.id === wsId)!
  const [text, setText] = React.useState("")
  const [task, setTask] = React.useState("")
  const send = () => { if (!text.trim()) return; dispatch({ type: "comment", id: ws.id, text: text.trim() }); setText("") }
  const render = (t: string) => t.split(/(@[A-Za-z]+)/g).map((p, i) => p.startsWith("@") ? <span key={i} className="rounded bg-sky-500/15 px-1 text-sky-300">{p}</span> : p)

  return (
    <div className="grid gap-4 @4xl/main:grid-cols-[1fr_340px]">
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><MessageSquareIcon className="size-4" />Discussion</CardTitle>
          <CardDescription>Shared thread for everyone on this case. Mention teammates with @name.</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex max-h-[380px] flex-col gap-4 overflow-y-auto pr-1">
            {ws.comments.length === 0 && <p className="py-6 text-center text-muted-foreground">No messages yet. Start the discussion.</p>}
            {ws.comments.map((c) => (
              <div key={c.id} className="flex gap-3">
                <MemberAvatar id={c.by} className="size-8" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm"><b>{memberOf(c.by).name}</b> <span className="text-xs text-muted-foreground">· {memberOf(c.by).role} · {fmtTime(c.at)}</span></p>
                  <p className="mt-0.5 text-sm">{render(c.text)}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="flex gap-2 border-t pt-4">
            <MemberAvatar id={ME} className="size-8" />
            <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Write a comment… (Ctrl+Enter to send)" className="min-h-12"
              onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send() }} />
            <Button size="icon" onClick={send} disabled={!text.trim()}><SendIcon /></Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader><CardTitle>Members</CardTitle><CardAction><Button size="xs" variant="outline" onClick={onInvite}><UserPlusIcon />Invite</Button></CardAction></CardHeader>
          <CardContent className="flex flex-col gap-2.5">
            {ws.members.map((id) => { const m = memberOf(id); return (
              <div key={id} className="flex items-center gap-2.5">
                <div className="relative"><MemberAvatar id={id} className="size-8" /><span className={cn("absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full border-2 border-card", m.online ? "bg-emerald-400" : "bg-muted-foreground/40")} /></div>
                <div className="min-w-0 flex-1"><p className="truncate text-sm">{m.name}{id === ws.lead && <span className="ml-1.5 text-[11px] text-amber-400">Lead</span>}</p><p className="truncate text-xs text-muted-foreground">{m.role} · {m.org}</p></div>
              </div>
            )})}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><ListChecksIcon className="size-4" />Tasks</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-2">
            {ws.tasks.map((t) => (
              <label key={t.id} className="flex cursor-pointer items-start gap-2 text-sm">
                <Checkbox checked={t.done} onCheckedChange={() => dispatch({ type: "toggleTask", id: ws.id, taskId: t.id })} className="mt-0.5" />
                <span className={cn("flex-1", t.done && "text-muted-foreground line-through")}>{t.text}</span>
                <MemberAvatar id={t.assignee} className="size-5" />
              </label>
            ))}
            <div className="flex gap-2 pt-1">
              <Input value={task} onChange={(e) => setTask(e.target.value)} placeholder="New task…" onKeyDown={(e) => { if (e.key === "Enter" && task.trim()) { dispatch({ type: "addTask", id: ws.id, text: task.trim(), assignee: ME }); setTask("") } }} />
              <Button size="icon" variant="outline" disabled={!task.trim()} onClick={() => { dispatch({ type: "addTask", id: ws.id, text: task.trim(), assignee: ME }); setTask("") }}><PlusIcon /></Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Activity</CardTitle></CardHeader>
          <CardContent className="flex max-h-64 flex-col gap-3 overflow-y-auto border-l pl-4 ml-6">
            {ws.activity.slice(0, 12).map((a) => (
              <div key={a.id} className="relative text-xs">
                <span className="absolute top-1 -left-[21px] size-2 rounded-full bg-muted-foreground/60" />
                <b>{memberOf(a.by).name.split(" ").slice(-1)[0]}</b> {a.text}<div className="text-muted-foreground">{fmtTime(a.at)}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
