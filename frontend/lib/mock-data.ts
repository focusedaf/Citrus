import type {
  Alert, EntityType, GraphEdge, GraphNode, Member, RiskLevel, Workspace,
} from "./types"

/** Fixed "demo now" so SSR + client render identical strings. 28 Sep 2026, 15:00 IST */
export const DEMO_NOW = Date.UTC(2026, 8, 28, 9, 30) / 1000
const H = 3600
const D = 86400

export const ME = "m1"

export const MEMBERS: Member[] = [
  { id: "m1", name: "Insp. Aarav Mehta", role: "Lead", org: "Cyber Cell, Pune", online: true },
  { id: "m2", name: "Asha Nair", role: "Analyst", org: "I4C, MHA", online: true },
  { id: "m3", name: "Rohan Iyer", role: "Forensics", org: "State FSL, Mumbai", online: false },
  { id: "m4", name: "Priya Deshmukh", role: "Legal", org: "Nodal Officer, NCRP", online: true },
  { id: "m5", name: "Kabir Singh", role: "Liaison", org: "VASP Compliance Desk", online: false },
]

export const ROLE_COLORS: Record<string, string> = {
  m1: "bg-amber-500/20 text-amber-300",
  m2: "bg-sky-500/20 text-sky-300",
  m3: "bg-emerald-500/20 text-emerald-300",
  m4: "bg-violet-500/20 text-violet-300",
  m5: "bg-rose-500/20 text-rose-300",
}

/** deterministic pseudo-address so mock data looks real and is stable */
function addr(seed: string): string {
  let h1 = 0x811c9dc5, h2 = 0x1b873593
  const out: string[] = []
  for (let i = 0; i < 40; i++) {
    const c = seed.charCodeAt(i % seed.length) + i * 31
    h1 = Math.imul(h1 ^ c, 16777619) >>> 0
    h2 = Math.imul(h2 + c, 2246822519) >>> 0
    out.push(((h1 ^ h2) & 15).toString(16))
  }
  return "0x" + out.join("")
}

type N = [key: string, label: string, type: EntityType, hop: number]
type E = [from: string, to: string, amount: number, token: string, hop: number, minutesAfter: number, spoofed?: boolean]

function build(prefix: string, t0: number, nodes: N[], edges: E[]) {
  const a = (k: string) => addr(prefix + k)
  const gn: GraphNode[] = nodes.map(([k, label, type, hop]) => ({
    id: a(k), label, type, hop,
    confidence: type === "unknown" ? "n/a" : type === "reported" ? "n/a" : "confirmed",
  }))
  const ge: GraphEdge[] = edges.map(([f, t, amount, token, hop, m, spoofed], i) => ({
    from: a(f), to: a(t), amount, token, hop,
    timestamp: t0 + m * 60,
    tx_hash: addr(`${prefix}tx${i}`).replace("0x", "0x") + addr(`${prefix}y${i}`).slice(2, 26),
    is_spoofed_token: !!spoofed,
  }))
  return { nodes: gn, edges: ge, start: a(nodes[0][0]) }
}

function summarize(nodes: GraphNode[], edges: GraphEdge[]) {
  const lab = (t: EntityType) => [...new Set(nodes.filter((n) => n.type === t).map((n) => n.label))]
  return {
    transactions: edges.length,
    counterparties: nodes.length - 1,
    depth: Math.max(...edges.map((e) => e.hop)) + 1,
    assets: [...new Set(edges.map((e) => e.token))],
    vasps: lab("vasp"), bridges: lab("bridge"), mixers: lab("mixer"),
    spoofed: [...new Set(edges.filter((e) => e.is_spoofed_token).map((e) => e.token))],
    crossChain: [] as string[],
  }
}

interface Seed {
  id: string; title: string; complaintId: string; state: string; status: Workspace["status"]
  score: number; level: RiskLevel; inr: number; daysAgo: number; lead: string; members: string[]
  reasons: string[]; nodes: N[]; edges: E[]; crossChain?: string[]
}

const seeds: Seed[] = [
  {
    id: "CT-1042", title: "Pig-butchering scam – fake trading app", complaintId: "NCRP/2026/MH/004871",
    state: "Maharashtra", status: "Freeze Requested", score: 92, level: "Critical", inr: 8_400_000, daysAgo: 1,
    lead: "m1", members: ["m1", "m2", "m3", "m4", "m5"],
    reasons: [
      "+40 funds passed through a known mixer/tumbler",
      "+30 funds reached a known VASP",
      "+20 rapid pass-through detected at 3 node(s) (forwarded within 60 min of receipt)",
      "+15 fan-out pattern (6 addresses funded directly from source)",
      "+15 deep layering (4 hops)",
      "+10 large single transfer (>= 5 ETH)",
    ],
    crossChain: ["BNB Smart Chain"],
    nodes: [
      ["v", "Victim-reported wallet", "reported", 0],
      ["a1", "Unidentified", "unknown", 1], ["a2", "Unidentified", "unknown", 1], ["a3", "Unidentified", "unknown", 1],
      ["a4", "Unidentified", "unknown", 1], ["a5", "Unidentified", "unknown", 1], ["a6", "Unidentified", "unknown", 1],
      ["b1", "Unidentified", "unknown", 2], ["b2", "Unidentified", "unknown", 2], ["b3", "Unidentified", "unknown", 2],
      ["mx", "Tornado Cash Router", "mixer", 2], ["br", "Multichain Bridge", "bridge", 2],
      ["c1", "Unidentified", "unknown", 3], ["c2", "Unidentified", "unknown", 3],
      ["x1", "Binance Hot Wallet 14", "vasp", 4], ["x2", "WazirX Deposit", "vasp", 4], ["x3", "OKX Deposit", "vasp", 4],
    ],
    edges: [
      ["v", "a1", 4.2, "ETH", 0, 4], ["v", "a2", 3.8, "ETH", 0, 6], ["v", "a3", 5.6, "ETH", 0, 9],
      ["v", "a4", 2.1, "ETH", 0, 11], ["v", "a5", 6.4, "ETH", 0, 14], ["v", "a6", 1.9, "ETH", 0, 19],
      ["a1", "b1", 4.1, "ETH", 1, 25], ["a2", "b1", 3.7, "ETH", 1, 30], ["a3", "mx", 5.5, "ETH", 1, 34],
      ["a4", "b2", 2.0, "ETH", 1, 41], ["a5", "br", 6.3, "ETH", 1, 48], ["a6", "b3", 1.8, "ETH", 1, 52],
      ["b1", "c1", 7.7, "ETH", 2, 70], ["mx", "c2", 5.4, "ETH", 2, 95], ["br", "c1", 6.2, "ETH", 2, 88],
      ["b2", "x2", 1.9, "ETH", 2, 101], ["b3", "x3", 1.7, "ETH", 2, 110],
      ["c1", "x1", 13.8, "ETH", 3, 150], ["c2", "x1", 5.3, "ETH", 3, 165],
    ],
  },
  {
    id: "CT-1041", title: "Phishing drainer – fake airdrop tokens", complaintId: "NCRP/2026/KA/003390",
    state: "Karnataka", status: "In Review", score: 78, level: "Critical", inr: 2_150_000, daysAgo: 2,
    lead: "m2", members: ["m2", "m3", "m1"],
    reasons: [
      "+35 spoofed/lookalike token detected (4 transfer(s))",
      "+25 funds crossed a known bridge (cross-chain movement)",
      "+20 rapid pass-through detected at 2 node(s)",
    ],
    crossChain: ["Arbitrum One"],
    nodes: [
      ["v", "Victim-reported wallet", "reported", 0],
      ["a1", "Unidentified", "unknown", 1], ["a2", "Unidentified", "unknown", 1],
      ["b1", "Unidentified", "unknown", 2], ["br", "Stargate Bridge", "bridge", 2],
      ["s1", "Uniswap V3 Router", "contract", 2],
      ["x1", "CoinDCX Hot Wallet", "vasp", 3],
    ],
    edges: [
      ["v", "a1", 0.9, "USDТ", 0, 3, true], ["v", "a2", 1.4, "ETH", 0, 5],
      ["a1", "s1", 0.9, "USDТ", 1, 12, true], ["a2", "br", 1.3, "ETH", 1, 15],
      ["s1", "b1", 0.85, "ETH", 2, 20], ["br", "b1", 1.25, "ETH", 2, 40],
      ["b1", "x1", 2.0, "ETH", 3, 62],
    ],
  },
  {
    id: "CT-1040", title: "Fake KYC → UPI-to-USDT laundering ring", complaintId: "NCRP/2026/DL/008122",
    state: "Delhi", status: "Tracing", score: 61, level: "High", inr: 5_900_000, daysAgo: 3,
    lead: "m1", members: ["m1", "m2", "m5"],
    reasons: [
      "+30 funds reached a known VASP",
      "+15 fan-in pattern (5 sources converging on one address)",
      "+15 deep layering (3 hops)",
    ],
    nodes: [
      ["v", "Victim-reported wallet", "reported", 0],
      ["a1", "Unidentified", "unknown", 1], ["a2", "Unidentified", "unknown", 1], ["a3", "Unidentified", "unknown", 1],
      ["b1", "Unidentified", "unknown", 2], ["b2", "Unidentified", "unknown", 2],
      ["x1", "WazirX Deposit", "vasp", 3], ["x2", "Binance Hot Wallet 8", "vasp", 3],
    ],
    edges: [
      ["v", "a1", 8.0, "ETH", 0, 5], ["v", "a2", 6.5, "ETH", 0, 8], ["v", "a3", 4.1, "ETH", 0, 12],
      ["a1", "b1", 7.9, "ETH", 1, 60], ["a2", "b1", 6.4, "ETH", 1, 75], ["a3", "b2", 4.0, "ETH", 1, 90],
      ["b1", "x1", 14.2, "ETH", 2, 180], ["b2", "x2", 3.9, "ETH", 2, 210],
    ],
  },
  {
    id: "CT-1039", title: "Telegram investment-group fraud", complaintId: "NCRP/2026/GJ/002714",
    state: "Gujarat", status: "In Review", score: 54, level: "High", inr: 1_240_000, daysAgo: 5,
    lead: "m2", members: ["m2", "m4"],
    reasons: ["+30 funds reached a known VASP", "+20 traced address also active on other chains (BNB Smart Chain)"],
    crossChain: ["BNB Smart Chain"],
    nodes: [
      ["v", "Victim-reported wallet", "reported", 0],
      ["a1", "Unidentified", "unknown", 1], ["a2", "Unidentified", "unknown", 1],
      ["x1", "OKX Deposit", "vasp", 2],
    ],
    edges: [["v", "a1", 2.2, "ETH", 0, 10], ["v", "a2", 1.1, "ETH", 0, 15], ["a1", "x1", 2.1, "ETH", 1, 120], ["a2", "x1", 1.0, "ETH", 1, 150]],
  },
  {
    id: "CT-1038", title: "Romance scam – small wallet cluster", complaintId: "NCRP/2026/TN/001988",
    state: "Tamil Nadu", status: "New", score: 33, level: "Medium", inr: 310_000, daysAgo: 6,
    lead: "m3", members: ["m3"],
    reasons: ["+15 deep layering (3 hops)", "+10 large single transfer (>= 5 ETH)"],
    nodes: [
      ["v", "Victim-reported wallet", "reported", 0], ["a1", "Unidentified", "unknown", 1],
      ["b1", "Unidentified", "unknown", 2], ["c1", "Unidentified", "unknown", 3],
    ],
    edges: [["v", "a1", 5.4, "ETH", 0, 8], ["a1", "b1", 5.3, "ETH", 1, 200], ["b1", "c1", 5.2, "ETH", 2, 400]],
  },
  {
    id: "CT-1036", title: "Sextortion – single hop to exchange", complaintId: "NCRP/2026/UP/000512",
    state: "Uttar Pradesh", status: "Closed", score: 12, level: "Low", inr: 45_000, daysAgo: 12,
    lead: "m4", members: ["m4", "m5"],
    reasons: [],
    nodes: [["v", "Victim-reported wallet", "reported", 0], ["x1", "Binance Hot Wallet 20", "vasp", 1]],
    edges: [["v", "x1", 0.4, "ETH", 0, 6]],
  },
]

function toWorkspace(s: Seed): Workspace {
  const t0 = DEMO_NOW - s.daysAgo * D - 5 * H
  const { nodes, edges } = build(s.id, t0, s.nodes, s.edges)
  const summary = { ...summarize(nodes, edges), crossChain: s.crossChain ?? [] }
  const lead = s.lead
  return {
    id: s.id, title: s.title, complaintId: s.complaintId, source: "NCRP/SAHYOG (mock)",
    victimState: s.state, address: nodes[0].id, chain: "Ethereum", status: s.status,
    riskScore: s.score, riskLevel: s.level, amountInr: s.inr, createdAt: t0,
    members: s.members, lead, nodes, edges, reasons: s.reasons, summary,
    evidenceHash: addr("hash" + s.id).slice(2) + addr("h2" + s.id).slice(2, 26),
    comments: [
      { id: `${s.id}-c1`, by: lead, at: t0 + 10 * 60, text: "Complaint ingested from NCRP. Auto-trace completed – reviewing the exchange endpoints first." },
      ...(s.members.length > 1 ? [{ id: `${s.id}-c2`, by: s.members[1], at: t0 + 2 * H, text: "Confirmed the hop pattern. Recommend prioritising the VASP deposit addresses for a freeze request." }] : []),
    ],
    activity: [
      { id: `${s.id}-a1`, by: lead, at: t0, text: "created this workspace from complaint " + s.complaintId },
      { id: `${s.id}-a2`, by: lead, at: t0 + 60, text: `ran automated trace (${edges.length} transactions, ${summary.depth} hops)` },
      { id: `${s.id}-a3`, by: lead, at: t0 + 90, text: `risk score computed: ${s.score}/100 (${s.level})` },
    ],
    tasks: s.status === "Closed" ? [] : [
      { id: `${s.id}-t1`, text: "Verify VASP attribution against labelled dataset", assignee: s.members[Math.min(1, s.members.length - 1)], done: true },
      { id: `${s.id}-t2`, text: "Draft freeze / preservation request to exchange compliance", assignee: s.members[s.members.length - 1], done: s.status === "Freeze Requested" },
      { id: `${s.id}-t3`, text: "Attach evidence bundle to FIR", assignee: lead, done: false },
    ],
    reports: [{ id: `${s.id}-r1`, name: `Investigation report – ${s.id}.pdf`, at: t0 + 2 * H, by: lead, kind: "PDF" },
      { id: `${s.id}-r2`, name: `Evidence bundle – ${s.id}.json`, at: t0 + 2 * H, by: lead, kind: "Evidence" }],
  }
}

export const WORKSPACES: Workspace[] = seeds.map(toWorkspace)

const alertSeeds: [string, RiskLevel, string, number, boolean][] = [
  ["CT-1042", "Critical", "Funds reached Binance Hot Wallet 14 after passing a mixer – 19.1 ETH in 165 min", 40, false],
  ["CT-1041", "Critical", "Spoofed USDТ token used in 4 transfers; funds bridged to Arbitrum", 26 * 60, false],
  ["CT-1042", "High", "Rapid pass-through: 3 intermediary wallets forwarded funds within 60 min", 90, false],
  ["CT-1040", "High", "Fan-in: 5 sources converging on one address before WazirX deposit", 3 * 24 * 60 - 30, true],
  ["CT-1039", "High", "Traced address also active on BNB Smart Chain", 5 * 24 * 60, true],
]
export const ALERTS: Alert[] = alertSeeds.map(([wid, level, message, minsAgo, ack], i) => {
  const w = WORKSPACES.find((x) => x.id === wid)!
  return { id: `AL-${200 - i}`, workspaceId: wid, address: w.address, level, message, at: DEMO_NOW - minsAgo * 60, acknowledged: ack }
})

/** 14-day trend for the dashboard chart */
export const TREND = Array.from({ length: 30 }, (_, i) => {
  const d = new Date(Date.UTC(2026, 8, 28) - (29 - i) * D * 1000)
  const wave = Math.round(6 + 4 * Math.sin(i / 3) + (i % 5))
  return {
    date: d.toISOString().slice(0, 10),
    critical: Math.max(0, Math.round(wave * 0.18)),
    high: Math.round(wave * 0.32),
    medium: Math.round(wave * 0.3),
    low: Math.round(wave * 0.2),
  }
})
