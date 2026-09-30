"use client";

import * as React from "react";
import Link from "next/link";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from "recharts";

import {
  AlertTriangleIcon,
  ArrowUpRightIcon,
  BanknoteIcon,
  BuildingIcon,
  FolderOpenIcon,
  ShieldAlertIcon,
  TrendingUpIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import {
  Button,
  buttonVariants,
} from "@/components/ui/button";

import {
  RiskBadge,
  StatusBadge,
  MemberStack,
} from "@/components/custom/bits";

import { getDashboardStats } from "@/lib/api";

import { fmtTime, inr } from "@/lib/format";
import { useStore } from "@/lib/store";
import type { Workspace } from "@/lib/types";
import { cn } from "@/lib/utils";

const trendCfg = {
  critical: {
    label: "Critical",
    color: "#ef4444",
  },
  high: {
    label: "High",
    color: "#f97316",
  },
  medium: {
    label: "Medium",
    color: "#eab308",
  },
  low: {
    label: "Low",
    color: "#22c55e",
  },
} satisfies ChartConfig;

type DashboardStats = {
  entity_counts?: {
    vasp?: number;
    mixer?: number;
    bridge?: number;
    contract?: number;
    unknown?: number;
  };

  top_exchanges?: {
    name: string;
    hits: number;
  }[];
};

const emptyStats: DashboardStats = {
  entity_counts: {
    vasp: 0,
    mixer: 0,
    bridge: 0,
    contract: 0,
    unknown: 0,
  },
  top_exchanges: [],
};

function normalizeDashboardStats(
  value: unknown,
): DashboardStats {
  if (!value || typeof value !== "object") {
    return emptyStats;
  }

  const raw = value as Record<string, unknown>;

  const entity =
    raw.entity_counts &&
    typeof raw.entity_counts === "object"
      ? (raw.entity_counts as Record<string, unknown>)
      : {};

  const exchanges = Array.isArray(raw.top_exchanges)
    ? raw.top_exchanges
    : [];

  return {
    entity_counts: {
      vasp:
        typeof entity.vasp === "number"
          ? entity.vasp
          : 0,

      mixer:
        typeof entity.mixer === "number"
          ? entity.mixer
          : 0,

      bridge:
        typeof entity.bridge === "number"
          ? entity.bridge
          : 0,

      contract:
        typeof entity.contract === "number"
          ? entity.contract
          : 0,

      unknown:
        typeof entity.unknown === "number"
          ? entity.unknown
          : 0,
    },

    top_exchanges: exchanges
      .filter(
        (
          item,
        ): item is {
          name: string;
          hits: number;
        } =>
          !!item &&
          typeof item === "object" &&
          typeof (item as Record<string, unknown>).name ===
            "string" &&
          typeof (item as Record<string, unknown>).hits ===
            "number",
      )
      .map((item) => ({
        name: item.name,
        hits: item.hits,
      })),
  };
}

function normalizeRiskLevel(
  level: string | undefined,
): "critical" | "high" | "medium" | "low" {
  const value = (level ?? "").toLowerCase();

  if (value.includes("critical")) {
    return "critical";
  }

  if (value.includes("high")) {
    return "high";
  }

  if (value.includes("medium")) {
    return "medium";
  }

  return "low";
}

function formatTrendDate(timestamp: number) {
  return new Date(
    timestamp * 1000,
  ).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

function getWorkspaceAmount(
  workspace: Workspace,
): number {
  return Number.isFinite(workspace.amountInr)
    ? workspace.amountInr
    : 0;
}

export default function DashboardPage() {
  const { state, dispatch } = useStore();

  const {
    workspaces,
    alerts,
  } = state;

  const [backendStats, setBackendStats] =
    React.useState<DashboardStats>(
      emptyStats,
    );

  const [loadingStats, setLoadingStats] =
    React.useState(true);

  /*
   * Dashboard statistics are supplementary only.
   *
   * The actual cases and alerts come from the workspace store.
   * This means the UI still works even when /dashboard/stats
   * returns zeros or is unavailable.
   */
  React.useEffect(() => {
    let cancelled = false;

    async function loadDashboardStats() {
      try {
        setLoadingStats(true);

        const data =
          await getDashboardStats(30);

        if (!cancelled) {
          setBackendStats(
            normalizeDashboardStats(data),
          );
        }
      } catch (error) {
        console.warn(
          "Dashboard statistics endpoint unavailable. Using workspace data.",
          error,
        );

        if (!cancelled) {
          setBackendStats(emptyStats);
        }
      } finally {
        if (!cancelled) {
          setLoadingStats(false);
        }
      }
    }

    loadDashboardStats();

    return () => {
      cancelled = true;
    };
  }, []);

  /*
   * ---------------------------------------------------------
   * PRIMARY DASHBOARD DATA
   * ---------------------------------------------------------
   *
   * These values come directly from the workspaces and alerts
   * already loaded by StoreProvider.
   */

  const active = React.useMemo(
    () =>
      workspaces.filter(
        (workspace) =>
          workspace.status !== "Closed",
      ),
    [workspaces],
  );

  const openAlerts = React.useMemo(
    () =>
      alerts.filter(
        (alert) => !alert.acknowledged,
      ),
    [alerts],
  );

  const criticalCases = React.useMemo(
    () =>
      workspaces.filter((workspace) => {
        const level =
          normalizeRiskLevel(
            workspace.riskLevel,
          );

        return (
          level === "critical" ||
          workspace.riskScore >= 75
        );
      }),
    [workspaces],
  );

  const fundsTraced = React.useMemo(
    () =>
      workspaces.reduce(
        (total, workspace) =>
          total +
          getWorkspaceAmount(workspace),
        0,
      ),
    [workspaces],
  );

  /*
   * Count unique VASPs from workspace attribution.
   *
   * This is more reliable for the current UI than depending
   * entirely on /dashboard/stats.
   */
  const workspaceVasps = React.useMemo(() => {
    const names = new Set<string>();

    for (const workspace of workspaces) {
      for (const vasp of
        workspace.summary?.vasps ?? []) {
        if (vasp?.trim()) {
          names.add(vasp.trim());
        }
      }
    }

    return [...names];
  }, [workspaces]);

  /*
   * Entity attribution from actual graph nodes.
   */
  const calculatedEntityCounts =
    React.useMemo(() => {
      const counts = {
        vasp: 0,
        mixer: 0,
        bridge: 0,
        contract: 0,
        unknown: 0,
      };

      for (const workspace of workspaces) {
        for (const node of workspace.nodes ?? []) {
          switch (node.type) {
            case "vasp":
              counts.vasp += 1;
              break;

            case "mixer":
              counts.mixer += 1;
              break;

            case "bridge":
              counts.bridge += 1;
              break;

            case "contract":
              counts.contract += 1;
              break;

            case "unknown":
              counts.unknown += 1;
              break;

            default:
              break;
          }
        }
      }

      return counts;
    }, [workspaces]);

  /*
   * Use actual workspace/node data first.
   *
   * Backend statistics are only used as fallback.
   */
  const entityCounts = [
    {
      type: "vasp",
      count:
        calculatedEntityCounts.vasp ||
        backendStats.entity_counts?.vasp ||
        0,
    },
    {
      type: "mixer",
      count:
        calculatedEntityCounts.mixer ||
        backendStats.entity_counts?.mixer ||
        0,
    },
    {
      type: "bridge",
      count:
        calculatedEntityCounts.bridge ||
        backendStats.entity_counts?.bridge ||
        0,
    },
    {
      type: "contract",
      count:
        calculatedEntityCounts.contract ||
        backendStats.entity_counts?.contract ||
        0,
    },
    {
      type: "unknown",
      count:
        calculatedEntityCounts.unknown ||
        backendStats.entity_counts?.unknown ||
        0,
    },
  ];

  /*
   * Build exchange/VASP ranking directly from workspaces.
   */
  const calculatedExchanges =
    React.useMemo(() => {
      const counts =
        new Map<string, number>();

      for (const workspace of workspaces) {
        for (const vasp of
          workspace.summary?.vasps ?? []) {
          const name = vasp?.trim();

          if (!name) continue;

          counts.set(
            name,
            (counts.get(name) ?? 0) + 1,
          );
        }
      }

      return [...counts.entries()]
        .map(([name, hits]) => ({
          name,
          hits,
        }))
        .sort(
          (a, b) =>
            b.hits - a.hits,
        )
        .slice(0, 6);
    }, [workspaces]);

  const vaspRows =
    calculatedExchanges.length > 0
      ? calculatedExchanges
      : backendStats.top_exchanges ?? [];

  /*
   * ---------------------------------------------------------
   * RISK TREND
   * ---------------------------------------------------------
   *
   * Use workspace creation dates.
   *
   * If the backend gives a timestamp outside the visible
   * 30-day window, don't silently lose it.
   */
  const trendData = React.useMemo(() => {
    const today = new Date();

    today.setHours(
      0,
      0,
      0,
      0,
    );

    const days = Array.from(
      { length: 30 },
      (_, index) => {
        const date = new Date(today);

        date.setDate(
          today.getDate() -
            (29 - index),
        );

        return date;
      },
    );

    const grouped = new Map<
      string,
      {
        date: string;
        critical: number;
        high: number;
        medium: number;
        low: number;
      }
    >();

    for (const date of days) {
      const key =
        date.toISOString().slice(0, 10);

      grouped.set(key, {
        date: key,
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
      });
    }

    for (const workspace of workspaces) {
      const timestamp =
        Number(workspace.createdAt);

      if (
        !Number.isFinite(timestamp) ||
        timestamp <= 0
      ) {
        continue;
      }

      const date =
        new Date(timestamp * 1000);

      const key =
        date.toISOString().slice(0, 10);

      const day =
        grouped.get(key);

      if (!day) continue;

      const risk =
        normalizeRiskLevel(
          workspace.riskLevel,
        );

      day[risk] += 1;
    }

    /*
     * If there are workspaces but none fall inside the
     * 30-day chart window, place them on today's point.
     *
     * This prevents the chart from looking completely broken
     * when old/mock timestamps are being used.
     */
    const hasData = [...grouped.values()].some(
      (day) =>
        day.critical +
          day.high +
          day.medium +
          day.low >
        0,
    );

    if (!hasData && workspaces.length > 0) {
      const todayKey =
        today
          .toISOString()
          .slice(0, 10);

      const todayData =
        grouped.get(todayKey);

      if (todayData) {
        for (const workspace of workspaces) {
          const risk =
            normalizeRiskLevel(
              workspace.riskLevel,
            );

          todayData[risk] += 1;
        }
      }
    }

    return [...grouped.values()];
  }, [workspaces]);

  const entityCfg = {
    count: {
      label: "Addresses",
    },

    vasp: {
      label: "Exchange / VASP",
      color: "#ef4444",
    },

    mixer: {
      label: "Mixer",
      color: "#a855f7",
    },

    bridge: {
      label: "Bridge",
      color: "#f59e0b",
    },

    contract: {
      label: "Contract",
      color: "#94a3b8",
    },

    unknown: {
      label: "Unidentified",
      color: "#3b82f6",
    },
  } satisfies ChartConfig;

  /*
   * ---------------------------------------------------------
   * KPI DATA
   * ---------------------------------------------------------
   */

  const kpis = [
    {
      label: "Active cases",
      value: active.length,
      icon: FolderOpenIcon,
      note: `${workspaces.length} total workspaces`,
      badge: "Live backend",
    },

    {
      label: "Critical cases",
      value: criticalCases.length,
      icon: ShieldAlertIcon,
      note: "Score ≥ 75, needs action",
      badge: `${openAlerts.length} open alerts`,
      danger: true,
    },

    {
      label: "Funds traced",
      value: inr(fundsTraced),
      icon: BanknoteIcon,
      note: "Across all complaints",
      badge: "NCRP linked",
    },

    {
      label: "VASPs identified",
      value: workspaceVasps.length,
      icon: BuildingIcon,
      note:
        workspaceVasps.length > 0
          ? "Identified by backend attribution"
          : "No VASPs identified",
      badge: "Freeze-ready",
    },
  ];

  return (
    <>
      <div className="grid grid-cols-1 gap-4 *:data-[slot=card]:bg-linear-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;

          return (
            <Card
              key={kpi.label}
              className="@container/card"
            >
              <CardHeader>
                <CardDescription>
                  {kpi.label}
                </CardDescription>

                <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                  {loadingStats &&
                  workspaces.length === 0
                    ? "—"
                    : kpi.value}
                </CardTitle>

                <CardAction>
                  <Badge
                    variant="outline"
                    className={cn(
                      kpi.danger &&
                        "border-red-500/40 text-red-400",
                    )}
                  >
                    <Icon />
                    {kpi.badge}
                  </Badge>
                </CardAction>
              </CardHeader>

              <CardFooter className="text-sm text-muted-foreground">
                {kpi.note}
              </CardFooter>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-4 @4xl/main:grid-cols-3">
        <Card className="@4xl/main:col-span-2">
          <CardHeader>
            <CardTitle>
              Cases by risk level
            </CardTitle>

            <CardDescription>
              Workspace cases grouped by risk
              level over the last 30 days
            </CardDescription>

            <CardAction>
              <Badge variant="outline">
                <TrendingUpIcon />
                30 day view
              </Badge>
            </CardAction>
          </CardHeader>

          <CardContent>
            <ChartContainer
              config={trendCfg}
              className="aspect-auto h-[260px] w-full"
            >
              <AreaChart
                data={trendData}
                margin={{
                  left: 8,
                  right: 8,
                  top: 8,
                  bottom: 0,
                }}
              >
                <CartesianGrid
                  vertical={false}
                  strokeDasharray="3 3"
                />

                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  minTickGap={32}
                  tickFormatter={(value) =>
                    formatTrendDate(
                      Math.floor(
                        new Date(
                          `${value}T00:00:00`,
                        ).getTime() /
                          1000,
                      ),
                    )
                  }
                />

                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  width={32}
                />

                <ChartTooltip
                  cursor={false}
                  content={
                    <ChartTooltipContent indicator="dot" />
                  }
                />

                <Area
                  dataKey="low"
                  type="monotone"
                  stackId="risk"
                  fill="var(--color-low)"
                  fillOpacity={0.45}
                  stroke="var(--color-low)"
                />

                <Area
                  dataKey="medium"
                  type="monotone"
                  stackId="risk"
                  fill="var(--color-medium)"
                  fillOpacity={0.45}
                  stroke="var(--color-medium)"
                />

                <Area
                  dataKey="high"
                  type="monotone"
                  stackId="risk"
                  fill="var(--color-high)"
                  fillOpacity={0.5}
                  stroke="var(--color-high)"
                />

                <Area
                  dataKey="critical"
                  type="monotone"
                  stackId="risk"
                  fill="var(--color-critical)"
                  fillOpacity={0.55}
                  stroke="var(--color-critical)"
                />

                <ChartLegend
                  content={
                    <ChartLegendContent />
                  }
                />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              Where the money lands
            </CardTitle>

            <CardDescription>
              Traced addresses by attributed entity
            </CardDescription>
          </CardHeader>

          <CardContent>
            <ChartContainer
              config={entityCfg}
              className="mx-auto aspect-square h-[220px]"
            >
              <PieChart>
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      hideLabel
                      nameKey="type"
                    />
                  }
                />

                <Pie
                  data={entityCounts}
                  dataKey="count"
                  nameKey="type"
                  innerRadius={55}
                  strokeWidth={2}
                >
                  {entityCounts.map(
                    (entity) => (
                      <Cell
                        key={entity.type}
                        fill={`var(--color-${entity.type})`}
                      />
                    ),
                  )}
                </Pie>

                <ChartLegend
                  content={
                    <ChartLegendContent
                      nameKey="type"
                    />
                  }
                />
              </PieChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 @4xl/main:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>
              Top exchanges hit
            </CardTitle>

            <CardDescription>
              Freeze-request candidates
            </CardDescription>
          </CardHeader>

          <CardContent>
            {vaspRows.length > 0 ? (
              <ChartContainer
                config={{
                  hits: {
                    label: "Deposit addresses",
                    color: "#ef4444",
                  },
                }}
                className="aspect-auto h-[210px] w-full"
              >
                <BarChart
                  data={vaspRows}
                  layout="vertical"
                  margin={{ left: 0 }}
                >
                  <CartesianGrid horizontal={false} />

                  <YAxis
                    dataKey="name"
                    type="category"
                    width={110}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11 }}
                  />

                  <XAxis
                    type="number"
                    hide
                  />

                  <ChartTooltip
                    cursor={false}
                    content={
                      <ChartTooltipContent hideLabel />
                    }
                  />

                  <Bar
                    dataKey="hits"
                    fill="var(--color-hits)"
                    radius={4}
                  />
                </BarChart>
              </ChartContainer>
            ) : (
              <div className="flex h-[210px] items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  No exchange attribution available.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="@4xl/main:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangleIcon className="size-4 text-red-400" />
              Live alerts
            </CardTitle>

            <CardDescription>
              {openAlerts.length} unacknowledged
            </CardDescription>

            <CardAction>
              <Link
                href="/alerts"
                className={buttonVariants({
                  variant: "ghost",
                  size: "sm",
                })}
              >
                View all
                <ArrowUpRightIcon />
              </Link>
            </CardAction>
          </CardHeader>

          <CardContent className="flex flex-col divide-y">
            {alerts
              .slice(0, 4)
              .map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0"
                >
                  <RiskBadge
                    level={alert.level}
                  />

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm">
                      {alert.message}
                    </p>

                    <p className="text-xs text-muted-foreground">
                      <Link
                        href={`/workspaces/${alert.workspaceId}`}
                        className="underline-offset-2 hover:underline"
                      >
                        {alert.workspaceId}
                      </Link>

                      {" · "}

                      {fmtTime(alert.at)}
                    </p>
                  </div>

                  {!alert.acknowledged ? (
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={() =>
                        dispatch({
                          type: "ack",
                          alertId:
                            alert.id,
                        })
                      }
                    >
                      Acknowledge
                    </Button>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      Ack’d
                    </span>
                  )}
                </div>
              ))}

            {alerts.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground">
                No alerts available.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            Active workspaces
          </CardTitle>

          <CardDescription>
            Each workspace holds the trace graph,
            alerts, reports and team discussion
            for one complaint
          </CardDescription>

          <CardAction>
            <Link
              href="/workspaces"
              className={buttonVariants({
                variant: "outline",
                size: "sm",
              })}
            >
              All workspaces
            </Link>
          </CardAction>
        </CardHeader>

        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  Case
                </TableHead>

                <TableHead>
                  Risk
                </TableHead>

                <TableHead>
                  Status
                </TableHead>

                <TableHead>
                  Amount
                </TableHead>

                <TableHead>
                  Attribution
                </TableHead>

                <TableHead>
                  Team
                </TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {active
                .slice(0, 5)
                .map(
                  (
                    workspace,
                    index,
                  ) => (
                    <TableRow
                      key={`${workspace.id}-${workspace.traceId ?? "local"}-${index}`}
                    >
                      <TableCell>
                        <Link
                          href={`/workspaces/${workspace.id}`}
                          className="font-medium hover:underline"
                        >
                          {workspace.id}
                        </Link>

                        <div className="max-w-[260px] truncate text-xs text-muted-foreground">
                          {workspace.title}
                        </div>
                      </TableCell>

                      <TableCell>
                        <RiskBadge
                          level={
                            workspace.riskLevel
                          }
                          score={
                            workspace.riskScore
                          }
                        />
                      </TableCell>

                      <TableCell>
                        <StatusBadge
                          status={
                            workspace.status
                          }
                        />
                      </TableCell>

                      <TableCell className="tabular-nums">
                        {inr(
                          getWorkspaceAmount(
                            workspace,
                          ),
                        )}
                      </TableCell>

                      <TableCell className="text-xs">
                        {(
                          workspace.summary
                            ?.vasps ?? []
                        ).join(", ") || (
                          <span className="text-muted-foreground">
                            Unattributed
                          </span>
                        )}
                      </TableCell>

                      <TableCell>
                        <MemberStack
                          ids={
                            workspace.members ??
                            []
                          }
                        />
                      </TableCell>
                    </TableRow>
                  ),
                )}

              {active.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="h-24 text-center text-muted-foreground"
                  >
                    No active workspaces.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}