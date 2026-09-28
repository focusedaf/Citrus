export type RiskLevel = "Low" | "Medium" | "High" | "Critical"
export type EntityType = "reported" | "vasp" | "bridge" | "mixer" | "contract" | "unknown"
export type CaseStatus = "New" | "Tracing" | "In Review" | "Freeze Requested" | "Closed"
export type Role = "Lead" | "Analyst" | "Forensics" | "Legal" | "Liaison"

export interface Member {
  id: string
  name: string
  role: Role
  org: string
  online?: boolean
}

export interface GraphNode {
  id: string // address
  label: string
  type: EntityType
  hop: number
  confidence?: "confirmed" | "heuristic" | "n/a"
  flagged?: boolean
  notes?: { by: string; text: string; at: number }[]
}

export interface GraphEdge {
  from: string
  to: string
  token: string
  amount: number
  hop: number
  timestamp: number
  tx_hash: string
  is_spoofed_token?: boolean
}

export interface Comment {
  id: string
  by: string // member id
  text: string
  at: number
}

export interface Activity {
  id: string
  by: string
  text: string
  at: number
}

export interface Task {
  id: string
  text: string
  assignee: string
  done: boolean
}

export interface Alert {
  id: string
  workspaceId: string
  address: string
  level: RiskLevel
  message: string
  at: number
  acknowledged: boolean
}

export interface Workspace {
  id: string // e.g. CT-1042
  traceId?: number // backend trace id, if live
  title: string
  complaintId: string // NCRP ref
  source: string
  victimState: string
  address: string
  chain: string
  status: CaseStatus
  riskScore: number
  riskLevel: RiskLevel
  amountInr: number
  createdAt: number
  members: string[]
  lead: string
  nodes: GraphNode[]
  edges: GraphEdge[]
  reasons: string[]
  summary: {
    transactions: number
    counterparties: number
    depth: number
    assets: string[]
    vasps: string[]
    bridges: string[]
    mixers: string[]
    spoofed: string[]
    crossChain: string[]
  }
  evidenceHash: string
  comments: Comment[]
  activity: Activity[]
  tasks: Task[]
  reports: { id: string; name: string; at: number; by: string; kind: "PDF" | "Evidence" }[]
}
