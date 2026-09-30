import type { RiskLevel } from "./types";

export const short = (
  a: string,
  f = 6,
  b = 4,
): string => {
  if (!a) return "—";

  return a.length > f + b + 3
    ? `${a.slice(0, f)}…${a.slice(-b)}`
    : a;
};

export const fmtTime = (ts: number | null | undefined): string => {
  const value = Number(ts);

  if (!Number.isFinite(value) || value <= 0) {
    return "—";
  }

  return new Date(value * 1000).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
};

export const fmtDate = (ts: number | null | undefined): string => {
  const value = Number(ts);

  if (!Number.isFinite(value) || value <= 0) {
    return "—";
  }

  return new Date(value * 1000).toLocaleDateString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

export const inr = (
  n: number | null | undefined,
): string => {
  const value = Number(n);

  if (!Number.isFinite(value)) {
    return "₹0";
  }

  if (value >= 1e7) {
    return `₹${(value / 1e7).toFixed(2)} Cr`;
  }

  if (value >= 1e5) {
    return `₹${(value / 1e5).toFixed(2)} L`;
  }

  return `₹${value.toLocaleString("en-IN")}`;
};

export const RISK_STYLE: Record<RiskLevel, string> = {
  Critical: "bg-red-500/15 text-red-400 border-red-500/30",
  High: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  Medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  Low: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

export const levelFromScore = (
  s: number | null | undefined,
): RiskLevel => {
  const score = Number(s);

  if (!Number.isFinite(score)) {
    return "Low";
  }

  if (score >= 75) return "Critical";
  if (score >= 50) return "High";
  if (score >= 25) return "Medium";

  return "Low";
};

export const initials = (
  name: string | null | undefined,
): string => {
  if (!name) return "—";

  return name
    .replace(/^(Insp\.|Dr\.|Mr\.|Ms\.)\s*/i, "")
    .split(/\s+/)
    .filter(Boolean)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
};