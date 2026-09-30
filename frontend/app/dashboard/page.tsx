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
import { Button, buttonVariants } from "@/components/ui/button";

import { RiskBadge, StatusBadge, MemberStack } from "@/components/custom/bits";

import { getDashboardStats } from "@/lib/api";

import { fmtTime, inr } from "@/lib/format";
import { useStore } from "@/lib/store";
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
  active_cases: number;
  total_workspaces: number;
  critical_cases: number;
  funds_traced_inr: number;
  vasps_identified: number;
  open_alerts: number;

  entity_counts: {
    vasp: number;
    mixer: number;
    bridge: number;
    contract: number;
    unknown: number;
  };

  top_exchanges: {
    name: string;
    hits: number;
  }[];
};

const emptyStats: DashboardStats = {
  active_cases: 0,
  total_workspaces: 0,
  critical_cases: 0,
  funds_traced_inr: 0,
  vasps_identified: 0,
  open_alerts: 0,

  entity_counts: {
    vasp: 0,
    mixer: 0,
    bridge: 0,
    contract: 0,
    unknown: 0,
  },

  top_exchanges: [],
};

/*
 * The backend response is runtime data, so we cannot assume
 * every nested object exists just because the TypeScript type
 * says it does.
 *
 * Normalize it once here so the rest of the dashboard can
 * safely use stats.entity_counts.vasp, etc.
 */
function normalizeDashboardStats(value: unknown): DashboardStats {
  if (!value || typeof value !== "object") {
    return emptyStats;
  }

  const raw = value as Record<string, unknown>;

  const rawEntityCounts =
    raw.entity_counts && typeof raw.entity_counts === "object"
      ? (raw.entity_counts as Record<string, unknown>)
      : {};

  const rawTopExchanges = Array.isArray(raw.top_exchanges)
    ? raw.top_exchanges
    : [];

  return {
    active_cases: typeof raw.active_cases === "number" ? raw.active_cases : 0,

    total_workspaces:
      typeof raw.total_workspaces === "number" ? raw.total_workspaces : 0,

    critical_cases:
      typeof raw.critical_cases === "number" ? raw.critical_cases : 0,

    funds_traced_inr:
      typeof raw.funds_traced_inr === "number" ? raw.funds_traced_inr : 0,

    vasps_identified:
      typeof raw.vasps_identified === "number" ? raw.vasps_identified : 0,

    open_alerts: typeof raw.open_alerts === "number" ? raw.open_alerts : 0,

    entity_counts: {
      vasp: typeof rawEntityCounts.vasp === "number" ? rawEntityCounts.vasp : 0,

      mixer:
        typeof rawEntityCounts.mixer === "number" ? rawEntityCounts.mixer : 0,

      bridge:
        typeof rawEntityCounts.bridge === "number" ? rawEntityCounts.bridge : 0,

      contract:
        typeof rawEntityCounts.contract === "number"
          ? rawEntityCounts.contract
          : 0,

      unknown:
        typeof rawEntityCounts.unknown === "number"
          ? rawEntityCounts.unknown
          : 0,
    },

    top_exchanges: rawTopExchanges
      .filter(
        (
          item,
        ): item is {
          name: string;
          hits: number;
        } =>
          !!item &&
          typeof item === "object" &&
          typeof (item as Record<string, unknown>).name === "string" &&
          typeof (item as Record<string, unknown>).hits === "number",
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

  if (value.includes("critical")) return "critical";
  if (value.includes("high")) return "high";
  if (value.includes("medium")) return "medium";

  return "low";
}

function formatTrendDate(timestamp: number) {
  return new Date(timestamp * 1000).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

export default function DashboardPage() {
  const { state, dispatch } = useStore();

  const { workspaces, alerts } = state;

  const [stats, setStats] = React.useState<DashboardStats>(emptyStats);

  const [loadingStats, setLoadingStats] = React.useState(true);

  const [statsError, setStatsError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    async function loadDashboardStats() {
      try {
        setLoadingStats(true);
        setStatsError(null);

        const data = await getDashboardStats(30);

        if (!cancelled) {
          /*
           * Never put raw backend JSON directly into
           * dashboard state.
           *
           * Normalize nested fields first.
           */
          setStats(normalizeDashboardStats(data));
        }
      } catch (error) {
        console.error("Failed to load dashboard statistics:", error);

        if (!cancelled) {
          setStatsError(
            error instanceof Error
              ? error.message
              : "Failed to load dashboard statistics",
          );

          /*
           * Keep the dashboard renderable even when
           * the statistics endpoint fails.
           */
          setStats(emptyStats);
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

  const active = workspaces.filter((w) => w.status !== "Closed");

  const openAlerts = alerts.filter((a) => !a.acknowledged);

  /*
   * Build the risk trend entirely on the frontend.
   *
   * No backend changes are required.
   * Workspace creation timestamps are grouped by day
   * and separated according to their risk level.
   */
  const trendData = React.useMemo(() => {
    const today = new Date();

    today.setHours(0, 0, 0, 0);

    const days = Array.from({ length: 30 }, (_, index) => {
      const date = new Date(today);

      date.setDate(today.getDate() - (29 - index));

      return date;
    });

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

    days.forEach((date) => {
      const key = date.toISOString().slice(0, 10);

      grouped.set(key, {
        date: key,
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
      });
    });

    workspaces.forEach((workspace) => {
      if (!workspace.createdAt) return;

      const date = new Date(workspace.createdAt * 1000);

      const key = date.toISOString().slice(0, 10);

      const day = grouped.get(key);

      if (!day) return;

      const risk = normalizeRiskLevel(workspace.riskLevel);

      day[risk] += 1;
    });

    return Array.from(grouped.values());
  }, [workspaces]);

  const entityCounts = [
    {
      type: "vasp",
      count: stats.entity_counts.vasp,
    },
    {
      type: "mixer",
      count: stats.entity_counts.mixer,
    },
    {
      type: "bridge",
      count: stats.entity_counts.bridge,
    },
    {
      type: "contract",
      count: stats.entity_counts.contract,
    },
    {
      type: "unknown",
      count: stats.entity_counts.unknown,
    },
  ];

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

  const vaspRows = stats.top_exchanges
    .map((exchange) => ({
      name: exchange.name,
      hits: exchange.hits,
    }))
    .slice(0, 6);

  const kpis = [
    {
      label: "Active cases",
      value: stats.active_cases,
      icon: FolderOpenIcon,
      note: `${stats.total_workspaces} total workspaces`,
      badge: "Live backend",
    },

    {
      label: "Critical cases",
      value: stats.critical_cases,
      icon: ShieldAlertIcon,
      note: "Score ≥ 75, needs action",
      badge: `${stats.open_alerts} open alerts`,
      danger: true,
    },

    {
      label: "Funds traced",
      value: inr(stats.funds_traced_inr),
      icon: BanknoteIcon,
      note: "Across all complaints",
      badge: "NCRP linked",
    },

    {
      label: "VASPs identified",
      value: stats.vasps_identified,
      icon: BuildingIcon,
      note:
        stats.vasps_identified > 0
          ? "Identified by backend attribution"
          : "No VASPs identified",
      badge: "Freeze-ready",
    },
  ];

  return (
    <>
      {statsError && (
        <Card className="border-red-500/40">
          <CardContent className="py-4">
            <p className="text-sm text-red-400">
              Dashboard statistics could not be loaded.
            </p>

            <p className="mt-1 text-xs text-muted-foreground">{statsError}</p>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 *:data-[slot=card]:bg-linear-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;

          return (
            <Card key={kpi.label} className="@container/card">
              <CardHeader>
                <CardDescription>{kpi.label}</CardDescription>

                <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                  {loadingStats ? "—" : kpi.value}
                </CardTitle>

                <CardAction>
                  <Badge
                    variant="outline"
                    className={cn(
                      kpi.danger && "border-red-500/40 text-red-400",
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
            <CardTitle>Cases by risk level</CardTitle>

            <CardDescription>
              Workspace cases grouped by risk level over the last 30 days
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
                <CartesianGrid vertical={false} strokeDasharray="3 3" />

                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  minTickGap={32}
                  tickFormatter={(value) =>
                    formatTrendDate(
                      Math.floor(
                        new Date(`${value}T00:00:00`).getTime() / 1000,
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
                  content={<ChartTooltipContent indicator="dot" />}
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

                <ChartLegend content={<ChartLegendContent />} />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Where the money lands</CardTitle>

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
                  content={<ChartTooltipContent hideLabel nameKey="type" />}
                />

                <Pie
                  data={entityCounts}
                  dataKey="count"
                  nameKey="type"
                  innerRadius={55}
                  strokeWidth={2}
                >
                  {entityCounts.map((entity) => (
                    <Cell
                      key={entity.type}
                      fill={`var(--color-${entity.type})`}
                    />
                  ))}
                </Pie>

                <ChartLegend content={<ChartLegendContent nameKey="type" />} />
              </PieChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 @4xl/main:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Top exchanges hit</CardTitle>

            <CardDescription>Freeze-request candidates</CardDescription>
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

                  <XAxis type="number" hide />

                  <ChartTooltip
                    cursor={false}
                    content={<ChartTooltipContent hideLabel />}
                  />

                  <Bar dataKey="hits" fill="var(--color-hits)" radius={4} />
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
            {alerts.slice(0, 4).map((alert) => (
              <div
                key={alert.id}
                className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0"
              >
                <RiskBadge level={alert.level} />

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">{alert.message}</p>

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
                        alertId: alert.id,
                      })
                    }
                  >
                    Acknowledge
                  </Button>
                ) : (
                  <span className="text-xs text-muted-foreground">Ack’d</span>
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
          <CardTitle>Active workspaces</CardTitle>

          <CardDescription>
            Each workspace holds the trace graph, alerts, reports and team
            discussion for one complaint
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
                <TableHead>Case</TableHead>

                <TableHead>Risk</TableHead>

                <TableHead>Status</TableHead>

                <TableHead>Amount</TableHead>

                <TableHead>Attribution</TableHead>

                <TableHead>Team</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {active.slice(0, 5).map((workspace) => (
                <TableRow key={workspace.id}>
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
                      level={workspace.riskLevel}
                      score={workspace.riskScore}
                    />
                  </TableCell>

                  <TableCell>
                    <StatusBadge status={workspace.status} />
                  </TableCell>

                  <TableCell className="tabular-nums">
                    {inr(workspace.amountInr)}
                  </TableCell>

                  <TableCell className="text-xs">
                    {(workspace.summary?.vasps ?? []).join(", ") || (
                      <span className="text-muted-foreground">
                        Unattributed
                      </span>
                    )}
                  </TableCell>

                  <TableCell>
                    <MemberStack ids={workspace.members ?? []} />
                  </TableCell>
                </TableRow>
              ))}

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
