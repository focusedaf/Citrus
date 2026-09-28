"use client"

import * as React from "react"
import Link from "next/link"
import { PlusIcon, SearchIcon } from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { buttonVariants } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { MemberStack, Mono, RiskBadge, StatusBadge } from "@/components/custom/bits"
import { fmtDate, inr, short } from "@/lib/format"
import { useStore } from "@/lib/store"

export default function WorkspacesPage() {
  const { state } = useStore()
  const [q, setQ] = React.useState("")
  const [status, setStatus] = React.useState("All")
  const list = state.workspaces.filter((w) =>
    (status === "All" || w.status === status) &&
    (`${w.id} ${w.title} ${w.address} ${w.complaintId}`.toLowerCase().includes(q.toLowerCase())))

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-sm">
          <SearchIcon className="absolute top-2 left-2.5 size-4 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search case, complaint ID or wallet…" className="pl-8" />
        </div>
        <Select value={status} onValueChange={(v) => v && setStatus(v)}>
          <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
          <SelectContent>{["All", "New", "Tracing", "In Review", "Freeze Requested", "Closed"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
        </Select>
        <Link href="/trace" className={buttonVariants({ className: "ml-auto" })}><PlusIcon />New workspace</Link>
      </div>

      <div className="grid gap-4 @2xl/main:grid-cols-2 @5xl/main:grid-cols-3">
        {list.map((w) => (
          <Link key={w.id} href={`/workspaces/${w.id}`} className="group">
            <Card className="h-full transition-colors group-hover:border-primary/40">
              <CardHeader>
                <div className="flex items-center justify-between"><span className="text-xs text-muted-foreground">{w.id} · {fmtDate(w.createdAt)}</span><RiskBadge level={w.riskLevel} score={w.riskScore} /></div>
                <CardTitle className="leading-snug">{w.title}</CardTitle>
                <CardDescription><Mono>{short(w.address, 10, 6)}</Mono> · {w.victimState}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span>{w.summary.transactions} txns</span><span>{w.summary.depth} hops</span><span>{inr(w.amountInr)}</span>
                </div>
                <div className="text-xs">{w.summary.vasps.length ? <>Reached: <b>{w.summary.vasps.join(", ")}</b></> : <span className="text-muted-foreground">No exchange reached yet</span>}</div>
              </CardContent>
              <CardFooter className="justify-between"><StatusBadge status={w.status} /><MemberStack ids={w.members} /></CardFooter>
            </Card>
          </Link>
        ))}
        {list.length === 0 && <p className="col-span-full py-12 text-center text-muted-foreground">No workspaces match.</p>}
      </div>
    </>
  )
}
