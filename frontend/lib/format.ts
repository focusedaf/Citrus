import type { RiskLevel } from "./types"

export const short = (a: string, f = 6, b = 4) => (a.length > f + b + 3 ? `${a.slice(0, f)}…${a.slice(-b)}` : a)

export const fmtTime = (ts: number) =>
  new Date(ts * 1000).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  })

export const fmtDate = (ts: number) =>
  new Date(ts * 1000).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })

export const inr = (n: number) => {
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${n.toLocaleString("en-IN")}`
}

export const RISK_STYLE: Record<RiskLevel, string> = {
  Critical: "bg-red-500/15 text-red-400 border-red-500/30",
  High: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  Medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  Low: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
}

export const levelFromScore = (s: number): RiskLevel => (s >= 75 ? "Critical" : s >= 50 ? "High" : s >= 25 ? "Medium" : "Low")

export const initials = (name: string) =>
  name.replace(/^(Insp\.|Dr\.|Mr\.|Ms\.)\s*/i, "").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()
