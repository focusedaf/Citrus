"use client"

import * as React from "react"

import { ME, MEMBERS } from "./mock-data"

import {
  getAlerts,
  getWorkspaces,
  updateStatus,
  addComment,
  addTask,
  toggleTask,
  inviteMember,
  acknowledgeAlert,
  flagNode,
  addNodeNote,
  generateReport,
} from "./api"

import type { Alert, CaseStatus, Workspace } from "./types"

interface State {
  workspaces: Workspace[]
  alerts: Alert[]
}

type Action =
  | { type: "hydrate"; state: State }
  | { type: "reset" }
  | { type: "addWorkspace"; ws: Workspace; alerts?: Alert[] }
  | { type: "setWorkspace"; ws: Workspace }
  | { type: "setAlerts"; alerts: Alert[] }
  | { type: "comment"; id: string; text: string }
  | { type: "status"; id: string; status: CaseStatus }
  | { type: "toggleTask"; id: string; taskId: string }
  | { type: "addTask"; id: string; text: string; assignee: string }
  | { type: "invite"; id: string; member: string }
  | { type: "ack"; alertId: string }
  | { type: "flagNode"; id: string; node: string }
  | { type: "noteNode"; id: string; node: string; text: string }
  | { type: "genReport"; id: string }

const uid = () => Math.random().toString(36).slice(2, 9)

const now = () => Math.floor(Date.now() / 1000)

const initial: State = {
  workspaces: [],
  alerts: [],
}

function withWs(
  s: State,
  id: string,
  fn: (w: Workspace) => Workspace
): State {
  return {
    ...s,
    workspaces: s.workspaces.map((w) =>
      w.id === id ? fn(w) : w
    ),
  }
}

const log = (w: Workspace, text: string): Workspace => ({
  ...w,
  activity: [
    {
      id: uid(),
      by: ME,
      at: now(),
      text,
    },
    ...w.activity,
  ],
})

function reducer(s: State, a: Action): State {
  switch (a.type) {
    case "hydrate":
      return a.state

    case "reset":
      return initial

    case "addWorkspace":
      return {
        workspaces: [
          a.ws,
          ...s.workspaces.filter((w) => w.id !== a.ws.id),
        ],
        alerts: [
          ...(a.alerts ?? []),
          ...s.alerts.filter(
            (x) =>
              !(a.alerts ?? []).some(
                (newAlert) => newAlert.id === x.id
              )
          ),
        ],
      }

    case "setWorkspace":
      return {
        ...s,
        workspaces: s.workspaces.map((w) =>
          w.id === a.ws.id ? a.ws : w
        ),
      }

    case "setAlerts":
      return {
        ...s,
        alerts: a.alerts,
      }

    case "comment":
      return withWs(s, a.id, (w) => ({
        ...log(w, "commented on the case"),
        comments: [
          ...w.comments,
          {
            id: uid(),
            by: ME,
            at: now(),
            text: a.text,
          },
        ],
      }))

    case "status":
      return withWs(s, a.id, (w) => ({
        ...log(w, `changed status to "${a.status}"`),
        status: a.status,
      }))

    case "toggleTask":
      return withWs(s, a.id, (w) => ({
        ...w,
        tasks: w.tasks.map((t) =>
          t.id === a.taskId
            ? { ...t, done: !t.done }
            : t
        ),
      }))

    case "addTask":
      return withWs(s, a.id, (w) => ({
        ...log(w, `added task "${a.text}"`),
        tasks: [
          ...w.tasks,
          {
            id: uid(),
            text: a.text,
            assignee: a.assignee,
            done: false,
          },
        ],
      }))

    case "invite":
      return withWs(s, a.id, (w) => {
        if (w.members.includes(a.member)) return w

        const m = MEMBERS.find((x) => x.id === a.member)

        return {
          ...log(
            w,
            `invited ${m?.name ?? "a collaborator"} to the workspace`
          ),
          members: [...w.members, a.member],
        }
      })

    case "ack":
      return {
        ...s,
        alerts: s.alerts.map((x) =>
          x.id === a.alertId
            ? { ...x, acknowledged: true }
            : x
        ),
      }

    case "flagNode":
      return withWs(s, a.id, (w) => ({
        ...log(
          w,
          `flagged ${a.node.slice(0, 10)}… for freeze request`
        ),
        nodes: w.nodes.map((n) =>
          n.id === a.node
            ? { ...n, flagged: !n.flagged }
            : n
        ),
      }))

    case "noteNode":
      return withWs(s, a.id, (w) => ({
        ...log(
          w,
          `annotated ${a.node.slice(0, 10)}…`
        ),
        nodes: w.nodes.map((n) =>
          n.id === a.node
            ? {
                ...n,
                notes: [
                  ...(n.notes ?? []),
                  {
                    by: ME,
                    text: a.text,
                    at: now(),
                  },
                ],
              }
            : n
        ),
      }))

    case "genReport":
      return withWs(s, a.id, (w) => w)
  }
}

const Ctx = React.createContext<{
  state: State
  dispatch: React.Dispatch<Action>
  ready: boolean
} | null>(null)

export function StoreProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const [state, reducerDispatch] = React.useReducer(
    reducer,
    initial
  )

  const [ready, setReady] = React.useState(false)

  const dispatch = React.useCallback(
    async (action: Action) => {
      try {
        switch (action.type) {
          case "status": {
            const ws = await updateStatus(
              action.id,
              action.status,
              ME
            )

            reducerDispatch({
              type: "setWorkspace",
              ws,
            })

            return
          }

          case "comment": {
            const ws = await addComment(
              action.id,
              action.text,
              ME
            )

            reducerDispatch({
              type: "setWorkspace",
              ws,
            })

            return
          }

          case "addTask": {
            const ws = await addTask(
              action.id,
              action.text,
              action.assignee,
              ME
            )

            reducerDispatch({
              type: "setWorkspace",
              ws,
            })

            return
          }

          case "toggleTask": {
            const ws = await toggleTask(
              action.id,
              action.taskId,
              ME
            )

            reducerDispatch({
              type: "setWorkspace",
              ws,
            })

            return
          }

          case "invite": {
            const ws = await inviteMember(
              action.id,
              action.member,
              ME
            )

            reducerDispatch({
              type: "setWorkspace",
              ws,
            })

            return
          }

          case "ack": {
            await acknowledgeAlert(action.alertId)

            const alerts = await getAlerts()

            reducerDispatch({
              type: "setAlerts",
              alerts,
            })

            return
          }

          case "flagNode": {
            const result = await flagNode(
              action.id,
              action.node,
              ME
            )

            reducerDispatch({
              type: "setWorkspace",
              ws: result.workspace,
            })

            return
          }

          case "noteNode": {
            const ws = await addNodeNote(
              action.id,
              action.node,
              action.text,
              ME
            )

            reducerDispatch({
              type: "setWorkspace",
              ws,
            })

            return
          }

          case "genReport": {
            await generateReport(action.id)

            const workspaces = await getWorkspaces()

            const ws = workspaces.find(
              (w) => w.id === action.id
            )

            if (ws) {
              reducerDispatch({
                type: "setWorkspace",
                ws,
              })
            }

            return
          }

          case "hydrate":
          case "reset":
          case "addWorkspace":
          case "setWorkspace":
          case "setAlerts":
            reducerDispatch(action)
            return

          default:
            return
        }
      } catch (error) {
        console.error(
          `Backend action "${action.type}" failed:`,
          error
        )
      }
    },
    []
  )

  React.useEffect(() => {
    let cancelled = false

    async function loadData() {
      try {
        const [workspaces, alerts] = await Promise.all([
          getWorkspaces(),
          getAlerts(),
        ])

        if (!cancelled) {
          reducerDispatch({
            type: "hydrate",
            state: {
              workspaces,
              alerts,
            },
          })
        }
      } catch (error) {
        console.error(
          "Failed to load backend data:",
          error
        )
      } finally {
        if (!cancelled) {
          setReady(true)
        }
      }
    }

    loadData()

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <Ctx.Provider
      value={{
        state,
        dispatch: dispatch as React.Dispatch<Action>,
        ready,
      }}
    >
      {children}
    </Ctx.Provider>
  )
}

export function useStore() {
  const c = React.useContext(Ctx)

  if (!c) {
    throw new Error("useStore outside StoreProvider")
  }

  return c
}