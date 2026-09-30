"use client"

import * as React from "react"
import Link from "next/link"
import { BellRingIcon, CheckCheckIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Mono, RiskBadge } from "@/components/custom/bits";
import { fmtTime, short } from "@/lib/format";
import { useStore } from "@/lib/store";

export default function AlertsPage() {
  const { state, dispatch } = useStore();
  const [f, setF] = React.useState("open");
  const list = state.alerts.filter((a) => (f === "open" ? !a.acknowledged : f === "critical" ? a.level === "Critical" : true));
  return (
    <Card className="border-cyan-400/[0.14] bg-[linear-gradient(145deg,rgba(10,26,48,0.78),rgba(3,11,23,0.88))] shadow-[0_16px_40px_rgba(0,0,0,0.4)]">
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-slate-100">
          <BellRingIcon className="size-5 text-cyan-400" />
          Alerts
        </CardTitle>
        <CardDescription className="text-slate-400 text-xs">
          Raised automatically when a trace scores High (≥50) or Critical (≥75)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <ToggleGroup
            value={[f]}
            onValueChange={(v) => v[0] && setF(v[0])}
            variant="outline"
            size="sm"
            className="border border-cyan-400/15 bg-slate-950/60 p-0.5 rounded-lg"
          >
            <ToggleGroupItem
              value="open"
              className="text-xs text-slate-400 data-[state=on]:bg-cyan-500/15 data-[state=on]:text-cyan-200 data-[state=on]:border-cyan-400/30"
            >
              Open
            </ToggleGroupItem>
            <ToggleGroupItem
              value="critical"
              className="text-xs text-slate-400 data-[state=on]:bg-rose-500/15 data-[state=on]:text-rose-300 data-[state=on]:border-rose-400/30"
            >
              Critical
            </ToggleGroupItem>
            <ToggleGroupItem
              value="all"
              className="text-xs text-slate-400 data-[state=on]:bg-cyan-500/15 data-[state=on]:text-cyan-200 data-[state=on]:border-cyan-400/30"
            >
              All
            </ToggleGroupItem>
          </ToggleGroup>
          <Button
            size="sm"
            variant="outline"
            className="ml-auto gap-1.5 border-cyan-400/20 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:text-cyan-200"
            onClick={() => state.alerts.forEach((a) => !a.acknowledged && dispatch({ type: "ack", alertId: a.id }))}
          >
            <CheckCheckIcon className="size-3.5" />
            Acknowledge all
          </Button>
        </div>
        <Table>
          <TableHeader className="border-cyan-400/[0.12]">
            <TableRow className="border-cyan-400/[0.08] hover:bg-transparent">
              <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Severity</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Alert</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Case</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Wallet</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Raised</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.map((a) => (
              <TableRow key={a.id} className="border-cyan-400/[0.08] hover:bg-cyan-500/[0.04] transition-colors">
                <TableCell>
                  <RiskBadge level={a.level} />
                </TableCell>
                <TableCell className="max-w-md whitespace-normal text-sm font-medium text-slate-200">
                  {a.message}
                </TableCell>
                <TableCell>
                  <Link href={`/workspaces/${a.workspaceId}`} className="font-mono text-xs font-semibold text-cyan-300 hover:text-cyan-200 hover:underline">
                    {a.workspaceId}
                  </Link>
                </TableCell>
                <TableCell>
                  <Mono>{short(a.address, 8, 6)}</Mono>
                </TableCell>
                <TableCell className="whitespace-nowrap font-mono text-xs text-slate-500">
                  {fmtTime(a.at)}
                </TableCell>
                <TableCell className="text-right">
                  {a.acknowledged ? (
                    <span className="font-mono text-xs text-slate-500">Acknowledged</span>
                  ) : (
                    <Button
                      size="xs"
                      variant="outline"
                      className="border-cyan-400/25 bg-slate-900/60 text-cyan-300 hover:border-cyan-400/45 hover:bg-cyan-500/10 hover:text-cyan-200"
                      onClick={() => dispatch({ type: "ack", alertId: a.id })}
                    >
                      Acknowledge
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {list.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-12 text-center text-slate-500">
                  All clear. No active alerts.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
