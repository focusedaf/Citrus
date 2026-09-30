"use client";

import { Avatar, AvatarFallback, AvatarGroup } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

import { MEMBERS, ROLE_COLORS } from "@/lib/mock-data";
import { RISK_STYLE, initials } from "@/lib/format";

import type { CaseStatus, RiskLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

export const memberOf = (id: string) =>
  MEMBERS.find((m) => m.id === id) ?? MEMBERS[0];

/* =========================================================
   RISK BADGE
   ========================================================= */

export function RiskBadge({
  level,
  score,
}: {
  level: RiskLevel;
  score?: number;
}) {
  return (
    <Badge
      variant="outline"
      className={cn(
        `
        rounded-full
        border
        px-2.5
        py-0.5
        text-[10px]
        font-semibold
        uppercase
        tracking-[0.04em]
        backdrop-blur-xl
        transition-all
        duration-200
        `,
        RISK_STYLE[level],
        "shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]",
      )}
    >
      <span
        className={cn(
          "mr-1.5 size-1.5 rounded-full",
          level === "Critical" && "bg-rose-400 shadow-[0_0_7px_rgba(251,113,133,0.8)]",
          level === "High" && "bg-orange-400 shadow-[0_0_7px_rgba(251,146,60,0.75)]",
          level === "Medium" && "bg-amber-400 shadow-[0_0_7px_rgba(251,191,36,0.7)]",
          level === "Low" && "bg-emerald-400 shadow-[0_0_7px_rgba(52,211,153,0.7)]",
        )}
      />

      {level}

      {score !== undefined ? (
        <span className="ml-0.5 opacity-80">· {score}</span>
      ) : null}
    </Badge>
  );
}

/* =========================================================
   STATUS BADGE
   ========================================================= */

const STATUS_STYLE: Record<CaseStatus, string> = {
  New: `
    border-sky-400/20
    bg-sky-400/[0.07]
    text-sky-300
    shadow-[0_0_16px_rgba(14,165,233,0.06)]
  `,

  Tracing: `
    border-cyan-400/20
    bg-cyan-400/[0.07]
    text-cyan-300
    shadow-[0_0_16px_rgba(6,182,212,0.07)]
  `,

  "In Review": `
    border-indigo-400/20
    bg-indigo-400/[0.07]
    text-indigo-300
    shadow-[0_0_16px_rgba(99,102,241,0.07)]
  `,

  "Freeze Requested": `
    border-rose-400/20
    bg-rose-400/[0.07]
    text-rose-300
    shadow-[0_0_18px_rgba(244,63,94,0.08)]
  `,

  Closed: `
    border-slate-500/15
    bg-slate-500/[0.045]
    text-slate-400
  `,
};

export function StatusBadge({ status }: { status: CaseStatus }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        `
        rounded-full
        border
        px-2.5
        py-0.5
        text-[10px]
        font-semibold
        uppercase
        tracking-[0.04em]
        backdrop-blur-xl
        transition-all
        duration-200
        `,
        STATUS_STYLE[status],
        "shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]",
      )}
    >
      <span
        className={cn(
          "mr-1.5 size-1.5 rounded-full",
          status === "New" &&
            "bg-sky-400 shadow-[0_0_7px_rgba(56,189,248,0.75)]",
          status === "Tracing" &&
            "bg-cyan-400 shadow-[0_0_7px_rgba(34,211,238,0.8)]",
          status === "In Review" &&
            "bg-indigo-400 shadow-[0_0_7px_rgba(129,140,248,0.75)]",
          status === "Freeze Requested" &&
            "bg-rose-400 shadow-[0_0_7px_rgba(251,113,133,0.8)]",
          status === "Closed" && "bg-slate-500",
        )}
      />

      {status}
    </Badge>
  );
}

/* =========================================================
   MEMBER AVATAR
   ========================================================= */

export function MemberAvatar({
  id,
  className,
}: {
  id: string;
  className?: string;
}) {
  const m = memberOf(id);

  return (
    <Avatar
      className={cn(
        `
        border
        border-cyan-400/20
        bg-slate-950/80
        shadow-[0_0_12px_rgba(6,182,212,0.08)]
        ring-1
        ring-white/[0.025]
        transition-all
        duration-200
        hover:border-cyan-300/35
        hover:shadow-[0_0_16px_rgba(6,182,212,0.14)]
        `,
        className,
      )}
      title={`${m.name} · ${m.role}`}
    >
      <AvatarFallback
        className={cn(
          `
          bg-slate-900/80
          text-[10px]
          font-semibold
          tracking-wide
          text-cyan-100
          backdrop-blur-xl
          `,
          ROLE_COLORS[id],
        )}
      >
        {initials(m.name)}
      </AvatarFallback>
    </Avatar>
  );
}

/* =========================================================
   MEMBER STACK
   ========================================================= */

export function MemberStack({ ids }: { ids: string[] }) {
  return (
    <AvatarGroup className="[&>*]:ring-[#030914]">
      {ids.map((id) => (
        <MemberAvatar
          key={id}
          id={id}
          className="size-6"
        />
      ))}
    </AvatarGroup>
  );
}

/* =========================================================
   MONOSPACE / BLOCKCHAIN TEXT
   ========================================================= */

export function Mono({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        `
        font-mono
        text-xs
        tracking-[-0.01em]
        text-cyan-200/80
        transition-colors
        `,
        className,
      )}
    >
      {children}
    </span>
  );
}