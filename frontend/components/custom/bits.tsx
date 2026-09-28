"use client"

import { Avatar, AvatarFallback, AvatarGroup } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { MEMBERS, ROLE_COLORS } from "@/lib/mock-data"
import { RISK_STYLE, initials } from "@/lib/format"
import type { CaseStatus, RiskLevel } from "@/lib/types"
import { cn } from "@/lib/utils"

export const memberOf = (id: string) => MEMBERS.find((m) => m.id === id) ?? MEMBERS[0]

export function RiskBadge({ level, score }: { level: RiskLevel; score?: number }) {
  return (
    <Badge variant="outline" className={cn("font-medium", RISK_STYLE[level])}>
      {level}{score !== undefined ? ` · ${score}` : ""}
    </Badge>
  )
}

const STATUS_STYLE: Record<CaseStatus, string> = {
  New: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  Tracing: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  "In Review": "bg-amber-500/15 text-amber-400 border-amber-500/30",
  "Freeze Requested": "bg-red-500/15 text-red-400 border-red-500/30",
  Closed: "bg-muted text-muted-foreground border-border",
}
export function StatusBadge({ status }: { status: CaseStatus }) {
  return <Badge variant="outline" className={STATUS_STYLE[status]}>{status}</Badge>
}

export function MemberAvatar({ id, className }: { id: string; className?: string }) {
  const m = memberOf(id)
  return (
    <Avatar className={className} title={`${m.name} · ${m.role}`}>
      <AvatarFallback className={cn("text-[10px] font-semibold", ROLE_COLORS[id])}>{initials(m.name)}</AvatarFallback>
    </Avatar>
  )
}

export function MemberStack({ ids }: { ids: string[] }) {
  return (
    <AvatarGroup>
      {ids.map((id) => <MemberAvatar key={id} id={id} className="size-6" />)}
    </AvatarGroup>
  )
}

export function Mono({ children, className }: { children: React.ReactNode; className?: string }) {
  return <span className={cn("font-mono text-xs", className)}>{children}</span>
}
