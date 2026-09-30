"use client";

import { useRef } from "react";
import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { CheckCircle2Icon, Loader2Icon, RadarIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { runTrace } from "@/lib/api";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const STEPS = [
  "Ingesting complaint from NCRP",
  "Fetching outgoing transactions",
  "Following hops (BFS)",
  "Tagging addresses against VASP dataset",
  "Scoring risk & generating evidence",
];

export default function TracePage() {
  const router = useRouter();
  const { dispatch } = useStore();

  const traceRequestKey = useRef<string | null>(null);

  const [address, setAddress] = React.useState("");
  const [hops, setHops] = React.useState("3");
  const [step, setStep] = React.useState(-1);

  const valid = /^0x[a-fA-F0-9]{40}$/.test(address.trim());
  const running = step >= 0;

  async function go() {
    if (!valid || running) return;

    const ticker = setInterval(() => {
      setStep((s) => (s < STEPS.length - 1 ? s + 1 : s));
    }, 900);

    setStep(0);

    try {
      if (!traceRequestKey.current) {
        traceRequestKey.current = crypto.randomUUID();
      }

      const res = await runTrace(
        address.trim(),
        1,
        Number(hops),
        traceRequestKey.current,
      );

      clearInterval(ticker);
      setStep(STEPS.length);

      dispatch({
        type: "addWorkspace",
        ws: res.ws,
        alerts: res.alert ? [res.alert] : [],
      });

      toast.success("Live trace complete");

      traceRequestKey.current = null;

      router.push(`/workspaces/${res.ws.id}`);
    } catch (error) {
      clearInterval(ticker);
      setStep(-1);

      toast.error(error instanceof Error ? error.message : "Trace failed");
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5 pt-2">
      <Card className="relative overflow-hidden border-cyan-400/[0.14] bg-[linear-gradient(145deg,rgba(10,26,48,0.8),rgba(3,11,23,0.9))] shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
        {/* Subtle ambient light */}
        <div className="pointer-events-none absolute -top-20 -right-20 size-48 rounded-full bg-cyan-400/10 blur-3xl" />

        <CardHeader>
          <CardTitle className="flex items-center gap-2.5 text-xl font-bold tracking-tight text-slate-100">
            <RadarIcon className="size-5 text-cyan-400 animate-pulse" />
            New investigation
          </CardTitle>

          <CardDescription className="text-slate-400 text-xs leading-relaxed">
            Enter a victim-reported wallet address to trace transactions,
            identify entities, assess risk, and create an investigation
            workspace.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="addr" className="text-xs font-semibold uppercase tracking-[0.08em] text-cyan-400/80">
              Wallet address
            </Label>

            <Input
              id="addr"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="0x..."
              className="font-mono text-sm border-cyan-400/20 bg-slate-950/70 text-cyan-200 placeholder:text-slate-500 focus:border-cyan-400/40 focus:ring-1 focus:ring-cyan-400/20"
              disabled={running}
            />

            {address.length > 0 && !valid && (
              <p className="text-xs text-rose-400 font-mono">
                Enter a valid 42-character Ethereum wallet address (0x...).
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-semibold uppercase tracking-[0.08em] text-cyan-400/80">
              Max hops
            </Label>

            <Select
              value={hops}
              onValueChange={(v) => v && setHops(v)}
              disabled={running}
            >
              <SelectTrigger className="w-36 border-cyan-400/20 bg-slate-950/70 text-slate-200 focus:border-cyan-400/40">
                <SelectValue />
              </SelectTrigger>

              <SelectContent className="border-cyan-400/20 bg-[#081224]/95 text-slate-200 backdrop-blur-2xl">
                {["2", "3"].map((h) => (
                  <SelectItem key={h} value={h} className="focus:bg-cyan-500/10 focus:text-cyan-200">
                    {h} hops
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            onClick={go}
            disabled={!valid || running}
            className="w-full gap-2 h-11 border border-cyan-300/25 bg-gradient-to-r from-cyan-500 via-sky-500 to-blue-600 text-white shadow-[0_0_24px_rgba(14,165,233,0.25)] hover:from-cyan-400 hover:via-sky-400 hover:to-blue-500 hover:shadow-[0_0_32px_rgba(14,165,233,0.35)] font-semibold tracking-wide transition-all active:scale-[0.99]"
          >
            {running ? <Loader2Icon className="animate-spin size-4" /> : <RadarIcon className="size-4" />}

            {running ? "Tracing on-chain hops..." : "Start trace"}
          </Button>
        </CardContent>
      </Card>

      {running && (
        <Card className="border-cyan-400/15 bg-slate-950/60 shadow-xl backdrop-blur-xl">
          <CardContent className="space-y-3 py-5">
            {STEPS.map((label, i) => (
              <div
                key={label}
                className={cn(
                  "flex items-center gap-3 text-sm transition-colors",
                  i < step
                    ? "text-emerald-300"
                    : i === step
                    ? "text-cyan-200 font-medium"
                    : "text-slate-500",
                )}
              >
                {i < step ? (
                  <CheckCircle2Icon className="size-4 text-emerald-400 shrink-0" />
                ) : i === step ? (
                  <Loader2Icon className="size-4 animate-spin text-cyan-400 shrink-0" />
                ) : (
                  <span className="size-4 rounded-full border border-slate-700 shrink-0" />
                )}

                <span>{label}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
