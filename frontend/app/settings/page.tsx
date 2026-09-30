"use client"

import { Settings2Icon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { API_URL } from "@/lib/api";

export default function SettingsPage() {
  return (
    <Card className="max-w-2xl border-cyan-400/[0.14] bg-[linear-gradient(145deg,rgba(10,26,48,0.78),rgba(3,11,23,0.88))] shadow-[0_16px_40px_rgba(0,0,0,0.4)]">
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-slate-100">
          <Settings2Icon className="size-5 text-cyan-400" />
          Settings
        </CardTitle>
        <CardDescription className="text-slate-400 text-xs">
          Investigation platform environment & telemetry configuration
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3.5 divide-y divide-cyan-400/[0.08] text-sm">
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs font-medium uppercase tracking-[0.08em] text-cyan-400/70">Backend API</span>
          <code className="rounded border border-cyan-400/20 bg-slate-950/70 px-2.5 py-1 font-mono text-xs text-cyan-300">{API_URL}</code>
        </div>
        <div className="flex items-center justify-between pt-3">
          <span className="text-xs font-medium uppercase tracking-[0.08em] text-cyan-400/70">Complaint source</span>
          <Badge variant="outline" className="border-cyan-400/25 bg-cyan-500/10 text-cyan-300 font-mono text-xs">
            NCRP / SAHYOG (mock)
          </Badge>
        </div>
        <div className="flex items-center justify-between pt-3">
          <span className="text-xs font-medium uppercase tracking-[0.08em] text-cyan-400/70">Active chain</span>
          <span className="font-mono text-xs text-slate-200">Ethereum mainnet (multi-chain planned)</span>
        </div>
        <div className="flex items-center justify-between pt-3">
          <span className="text-xs font-medium uppercase tracking-[0.08em] text-cyan-400/70">Risk engine</span>
          <span className="font-mono text-xs text-slate-200">Rule-based v1 (GNN heuristics planned)</span>
        </div>
      </CardContent>
    </Card>
  );
}
