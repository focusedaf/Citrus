"use client";

import * as React from "react";

import { ME, MEMBERS } from "./mock-data";

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
} from "./api";

import type { Alert, CaseStatus, Workspace } from "./types";

interface State {
  workspaces: Workspace[];
  alerts: Alert[];
}

type Action =
  | {
      type: "hydrate";
      state: State;
    }
  | {
      type: "reset";
    }
  | {
      type: "addWorkspace";
      ws: Workspace;
      alerts?: Alert[];
    }
  | {
      type: "setWorkspace";
      ws: Workspace;
    }
  | {
      type: "setAlerts";
      alerts: Alert[];
    }
  | {
      type: "comment";
      id: string;
      text: string;
    }
  | {
      type: "status";
      id: string;
      status: CaseStatus;
    }
  | {
      type: "toggleTask";
      id: string;
      taskId: string;
    }
  | {
      type: "addTask";
      id: string;
      text: string;
      assignee: string;
    }
  | {
      type: "invite";
      id: string;
      member: string;
    }
  | {
      type: "ack";
      alertId: string;
    }
  | {
      type: "flagNode";
      id: string;
      node: string;
    }
  | {
      type: "noteNode";
      id: string;
      node: string;
      text: string;
    }
  | {
      type: "genReport";
      id: string;
    };

const uid = () => Math.random().toString(36).slice(2, 9);

const now = () => Math.floor(Date.now() / 1000);

const initial: State = {
  workspaces: [],
  alerts: [],
};

function withWs(
  state: State,
  id: string,
  fn: (workspace: Workspace) => Workspace,
): State {
  return {
    ...state,
    workspaces: state.workspaces.map((workspace) =>
      workspace.id === id ? fn(workspace) : workspace,
    ),
  };
}

const log = (workspace: Workspace, text: string): Workspace => ({
  ...workspace,
  activity: [
    {
      id: uid(),
      by: ME,
      at: now(),
      text,
    },
    ...(workspace.activity ?? []),
  ],
});

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "hydrate":
      return {
        workspaces: action.state.workspaces ?? [],
        alerts: action.state.alerts ?? [],
      };

    case "reset":
      return initial;

    case "addWorkspace": {
      const existingWorkspace = state.workspaces.some(
        (workspace) => workspace.id === action.ws.id,
      );

      const incomingAlerts = action.alerts ?? [];

      const mergedAlerts = [
        ...incomingAlerts,
        ...state.alerts.filter(
          (existingAlert) =>
            !incomingAlerts.some(
              (newAlert) => newAlert.id === existingAlert.id,
            ),
        ),
      ];

      return {
        workspaces: existingWorkspace
          ? state.workspaces.map((workspace) =>
              workspace.id === action.ws.id ? action.ws : workspace,
            )
          : [action.ws, ...state.workspaces],
        alerts: mergedAlerts,
      };
    }

    case "setWorkspace": {
      const exists = state.workspaces.some(
        (workspace) => workspace.id === action.ws.id,
      );

      return {
        ...state,
        workspaces: exists
          ? state.workspaces.map((workspace) =>
              workspace.id === action.ws.id ? action.ws : workspace,
            )
          : [action.ws, ...state.workspaces],
      };
    }

    case "setAlerts":
      return {
        ...state,
        alerts: action.alerts ?? [],
      };

    case "status":
      return withWs(state, action.id, (workspace) => ({
        ...log(workspace, `changed status to "${action.status}"`),
        status: action.status,
      }));

    case "comment":
      return withWs(state, action.id, (workspace) => ({
        ...log(workspace, "commented on the case"),
        comments: [
          ...(workspace.comments ?? []),
          {
            id: uid(),
            by: ME,
            at: now(),
            text: action.text,
          },
        ],
      }));

    case "toggleTask":
      return withWs(state, action.id, (workspace) => ({
        ...workspace,
        tasks: (workspace.tasks ?? []).map((task) =>
          task.id === action.taskId
            ? {
                ...task,
                done: !task.done,
              }
            : task,
        ),
      }));

    case "addTask":
      return withWs(state, action.id, (workspace) => ({
        ...log(workspace, `added task "${action.text}"`),
        tasks: [
          ...(workspace.tasks ?? []),
          {
            id: uid(),
            text: action.text,
            assignee: action.assignee,
            done: false,
          },
        ],
      }));

    case "invite":
      return withWs(state, action.id, (workspace) => {
        if (workspace.members.includes(action.member)) {
          return workspace;
        }

        const member = MEMBERS.find((item) => item.id === action.member);

        return {
          ...log(
            workspace,
            `invited ${member?.name ?? "a collaborator"} to the workspace`,
          ),
          members: [...workspace.members, action.member],
        };
      });

    case "ack":
      return {
        ...state,
        alerts: state.alerts.map((alert) =>
          alert.id === action.alertId
            ? {
                ...alert,
                acknowledged: true,
              }
            : alert,
        ),
      };

    case "flagNode":
      return withWs(state, action.id, (workspace) => ({
        ...log(
          workspace,
          `flagged ${action.node.slice(0, 10)}… for freeze request`,
        ),
        nodes: workspace.nodes.map((node) =>
          node.id === action.node
            ? {
                ...node,
                flagged: !node.flagged,
              }
            : node,
        ),
      }));

    case "noteNode":
      return withWs(state, action.id, (workspace) => ({
        ...log(workspace, `annotated ${action.node.slice(0, 10)}…`),
        nodes: workspace.nodes.map((node) =>
          node.id === action.node
            ? {
                ...node,
                notes: [
                  ...(node.notes ?? []),
                  {
                    by: ME,
                    text: action.text,
                    at: now(),
                  },
                ],
              }
            : node,
        ),
      }));

    case "genReport":
      return withWs(state, action.id, (workspace) => workspace);

    default:
      return state;
  }
}

const Ctx = React.createContext<{
  state: State;
  dispatch: React.Dispatch<Action>;
  ready: boolean;
} | null>(null);

export function StoreProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, reducerDispatch] = React.useReducer(reducer, initial);
  const [ready, setReady] = React.useState(false);

  const dispatch = React.useCallback(async (action: Action) => {
    try {
      switch (action.type) {
        case "status": {
          /*
           * IMPORTANT:
           * Update the local store immediately.
           * This makes New -> Tracing, Tracing -> In Review, etc.
           * appear instantly without requiring a page refresh.
           */
          reducerDispatch(action);

          try {
            /*
             * Persist the status change on the backend.
             */
            const workspace = await updateStatus(
              action.id,
              action.status,
              ME,
            );

            /*
             * If the backend returns a workspace, sync it back into
             * the store. This keeps the frontend consistent with the
             * backend after the request completes.
             */
            if (workspace) {
              reducerDispatch({
                type: "setWorkspace",
                ws: workspace,
              });
            }
          } catch (error) {
            console.error(
              "Failed to update workspace status:",
              error,
            );

            /*
             * If the backend update fails, reload the workspace list
             * so the UI reflects the actual backend state.
             */
            try {
              const workspaces = await getWorkspaces(100);

              const updatedWorkspace = workspaces.find(
                (workspace) => workspace.id === action.id,
              );

              if (updatedWorkspace) {
                reducerDispatch({
                  type: "setWorkspace",
                  ws: updatedWorkspace,
                });
              }
            } catch (refreshError) {
              console.error(
                "Failed to refresh workspace after status update:",
                refreshError,
              );
            }
          }

          return;
        }

        case "comment": {
          const workspace = await addComment(
            action.id,
            action.text,
            ME,
          );

          reducerDispatch({
            type: "setWorkspace",
            ws: workspace,
          });

          return;
        }

        case "addTask": {
          const workspace = await addTask(
            action.id,
            action.text,
            action.assignee,
            ME,
          );

          reducerDispatch({
            type: "setWorkspace",
            ws: workspace,
          });

          return;
        }

        case "toggleTask": {
          const workspace = await toggleTask(
            action.id,
            action.taskId,
            ME,
          );

          reducerDispatch({
            type: "setWorkspace",
            ws: workspace,
          });

          return;
        }

        case "invite": {
          const workspace = await inviteMember(
            action.id,
            action.member,
            ME,
          );

          reducerDispatch({
            type: "setWorkspace",
            ws: workspace,
          });

          return;
        }

        case "ack": {
          await acknowledgeAlert(action.alertId);

          const alerts = await getAlerts(500);

          reducerDispatch({
            type: "setAlerts",
            alerts,
          });

          return;
        }

        case "flagNode": {
          const result = await flagNode(
            action.id,
            action.node,
            ME,
          );

          reducerDispatch({
            type: "setWorkspace",
            ws: result.workspace,
          });

          return;
        }

        case "noteNode": {
          const workspace = await addNodeNote(
            action.id,
            action.node,
            action.text,
            ME,
          );

          reducerDispatch({
            type: "setWorkspace",
            ws: workspace,
          });

          return;
        }

        case "genReport": {
          await generateReport(action.id);

          const workspaces = await getWorkspaces(100);

          const workspace = workspaces.find(
            (item) => item.id === action.id,
          );

          if (workspace) {
            reducerDispatch({
              type: "setWorkspace",
              ws: workspace,
            });
          }

          return;
        }

        case "hydrate":
        case "reset":
        case "addWorkspace":
        case "setWorkspace":
        case "setAlerts":
          reducerDispatch(action);
          return;

        default:
          return;
      }
    } catch (error) {
      console.error(
        `Backend action "${action.type}" failed:`,
        error,
      );
    }
  }, []);

  React.useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        const [workspaces, alerts] = await Promise.all([
          getWorkspaces(100),
          getAlerts(500),
        ]);

        if (!cancelled) {
          reducerDispatch({
            type: "hydrate",
            state: {
              workspaces,
              alerts,
            },
          });
        }
      } catch (error) {
        console.error(
          "Failed to load backend data:",
          error,
        );
      } finally {
        if (!cancelled) {
          setReady(true);
        }
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, []);

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
  );
}

export function useStore() {
  const context = React.useContext(Ctx);

  if (!context) {
    throw new Error("useStore outside StoreProvider");
  }

  return context;
}