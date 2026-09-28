"use client"
import * as React from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { CheckCircle2Icon, Loader2Icon, RadarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { runTrace } from "@/lib/api"
import { useStore } from "@/lib/store"
import { cn } from "@/lib/utils"

const STEPS = ["Ingesting complaint from NCRP", "Fetching outgoing transactions (Etherscan)", "Following hops (BFS)", "Tagging addresses against VASP dataset", "Scoring risk & generating evidence"]
const DEMO_ADDR = "0x1ab4973a48dc892cd9971ece8e01dcc7688f8f23"

export default function TracePage() {
  const router = useRouter()
  const { dispatch } = useStore()
  const [address, setAddress] = React.useState("")
  const [hops, setHops] = React.useState("3")
  const [step, setStep] = React.useState(-1)
  const valid = /^0x[a-fA-F0-9]{40}$/.test(address.trim())
  const running = step >= 0

  async function go() {
    setStep(0)
    const ticker = setInterval(() => setStep((s) => (s < STEPS.length - 1 ? s + 1 : s)), 900)
    const res = await runTrace(address.trim(), Number(hops))
    clearInterval(ticker)
    setStep(STEPS.length)
    dispatch({ type: "addWorkspace", ws: res.ws, alerts: res.alert ? [res.alert] : [] })
    toast[res.source === "live" ? "success" : "info"](res.source === "live" ? "Live trace complete" : "Backend unreachable – loaded demo dataset")
    setTimeout(() => router.push(`/workspaces/${res.ws.id}`), 500)
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><RadarIcon className="size-5" />New investigation</CardTitle>
          <CardDescription>Paste a victim-reported wallet address. Citrus traces it across hops, attributes exchanges, scores the risk, and opens a workspace for your team.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="addr">Wallet address</Label>
            <Input id="addr" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="0x…" className="font-mono" disabled={running} />
            <button type="button" className="text-xs text-muted-foreground underline-offset-2 hover:underline" onClick={() => setAddress(DEMO_ADDR)}>Use demo address</button>
          </div>
          <div className="space-y-1.5">
            <Label>Max hops</Label>
            <Select value={hops} onValueChange={(v) => v && setHops(v)} disabled={running}>
              <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
              <SelectContent>{["2", "3", "4", "5"].map((h) => <SelectItem key={h} value={h}>{h} hops</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <Button onClick={go} disabled={!valid || running} className="w-full">{running ? <Loader2Icon className="animate-spin" /> : <RadarIcon />}{running ? "Tracing…" : "Start trace"}</Button>
        </CardContent>
      </Card>

      {running && (
        <Card><CardContent className="space-y-2.5 py-5">
          {STEPS.map((s, i) => (
            <div key={s} className={cn("flex items-center gap-2.5 text-sm", i > step && "text-muted-foreground/50")}>
              {i < step ? <CheckCircle2Icon className="size-4 text-emerald-400" /> : i === step ? <Loader2Icon className="size-4 animate-spin" /> : <span className="size-4 rounded-full border" />}{s}
            </div>
          ))}
        </CardContent></Card>
      )}
    </div>
  )
}
