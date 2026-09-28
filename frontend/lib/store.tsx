"use client"

import * as React from "react"
import { ALERTS, ME, MEMBERS, WORKSPACES } from "./mock-data"
import type { Alert, CaseStatus, Workspace } from "./types"

interface State {
  workspaces: Workspace[]
  alerts: Alert[]
}

type Action =
  | { type: "hydrate"; state: State }
  | { type: "reset" }
  | { type: "addWorkspace"; ws: Workspace; alerts?: Alert[] }
  | { type: "comment"; id: string; text: string }
  | { type: "status"; id: string; status: CaseStatus }
  | { type: "toggleTask"; id: string; taskId: string }
  | { type: "addTask"; id: string; text: string; assignee: string }
  | { type: "invite"; id: string; member: string }
  | { type: "ack"; alertId: string }
  | { type: "flagNode"; id: string; node: string }
  | { type: "noteNode"; id: string; node: string; text: string }
  | { type: "genReport"; id: string }

const KEY = "citrus-state-v1"
const uid = () => Math.random().toString(36).slice(2, 9)
const now = () => Math.floor(Date.now() / 1000)
const initial: State = { workspaces: WORKSPACES, alerts: ALERTS }

function withWs(s: State, id: string, fn: (w: Workspace) => Workspace): State {
  return { ...s, workspaces: s.workspaces.map((w) => (w.id === id ? fn(w) : w)) }
}
const log = (w: Workspace, text: string): Workspace => ({
  ...w,
  activity: [{ id: uid(), by: ME, at: now(), text }, ...w.activity],
})

function reducer(s: State, a: Action): State {
  switch (a.type) {
    case "hydrate": return a.state
    case "reset": return initial
    case "addWorkspace": return { workspaces: [a.ws, ...s.workspaces], alerts: [...(a.alerts ?? []), ...s.alerts] }
    case "comment":
      return withWs(s, a.id, (w) => ({
        ...log(w, "commented on the case"),
        comments: [...w.comments, { id: uid(), by: ME, at: now(), text: a.text }],
      }))
    case "status":
      return withWs(s, a.id, (w) => ({ ...log(w, `changed status to “${a.status}”`), status: a.status }))
    case "toggleTask":
      return withWs(s, a.id, (w) => ({ ...w, tasks: w.tasks.map((t) => (t.id === a.taskId ? { ...t, done: !t.done } : t)) }))
    case "addTask":
      return withWs(s, a.id, (w) => ({
        ...log(w, `added task “${a.text}”`),
        tasks: [...w.tasks, { id: uid(), text: a.text, assignee: a.assignee, done: false }],
      }))
    case "invite":
      return withWs(s, a.id, (w) => {
        if (w.members.includes(a.member)) return w
        const m = MEMBERS.find((x) => x.id === a.member)
        return { ...log(w, `invited ${m?.name ?? "a collaborator"} to the workspace`), members: [...w.members, a.member] }
      })
    case "ack":
      return { ...s, alerts: s.alerts.map((x) => (x.id === a.alertId ? { ...x, acknowledged: true } : x)) }
    case "flagNode":
      return withWs(s, a.id, (w) => ({
        ...log(w, `flagged ${a.node.slice(0, 10)}… for freeze request`),
        nodes: w.nodes.map((n) => (n.id === a.node ? { ...n, flagged: !n.flagged } : n)),
      }))
    case "noteNode":
      return withWs(s, a.id, (w) => ({
        ...log(w, `annotated ${a.node.slice(0, 10)}…`),
        nodes: w.nodes.map((n) =>
          n.id === a.node ? { ...n, notes: [...(n.notes ?? []), { by: ME, text: a.text, at: now() }] } : n),
      }))
    case "genReport":
      return withWs(s, a.id, (w) => ({
        ...log(w, "generated a new investigation report"),
        reports: [{ id: uid(), name: `Investigation report – ${w.id} (v${w.reports.length + 1}).pdf`, at: now(), by: ME, kind: "PDF" }, ...w.reports],
      }))
  }
}

const Ctx = React.createContext<{ state: State; dispatch: React.Dispatch<Action>; ready: boolean } | null>(null)

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = React.useReducer(reducer, initial)
  const [ready, setReady] = React.useState(false)

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY)
      if (raw) dispatch({ type: "hydrate", state: JSON.parse(raw) })
    } catch {}
    setReady(true)
  }, [])

  React.useEffect(() => {
    if (!ready) return
    try { localStorage.setItem(KEY, JSON.stringify(state)) } catch {}
  }, [state, ready])

  return <Ctx.Provider value={{ state, dispatch, ready }}>{children}</Ctx.Provider>
}

export function useStore() {
  const c = React.useContext(Ctx)
  if (!c) throw new Error("useStore outside StoreProvider")
  return c
}
