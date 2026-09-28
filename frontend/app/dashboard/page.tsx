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
import { TREND } from "@/lib/mock-data";
import { fmtTime, inr } from "@/lib/format";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const trendCfg = {
  critical: { label: "Critical", color: "#ef4444" },
  high: { label: "High", color: "#f97316" },
  medium: { label: "Medium", color: "#eab308" },
  low: { label: "Low", color: "#22c55e" },
} satisfies ChartConfig;

export default function DashboardPage() {
  const { state, dispatch } = useStore();
  const { workspaces, alerts } = state;

  const active = workspaces.filter((w) => w.status !== "Closed");
  const openAlerts = alerts.filter((a) => !a.acknowledged);
  const traced = workspaces.reduce((s, w) => s + w.amountInr, 0);
  const vaspSet = new Set(workspaces.flatMap((w) => w.summary.vasps));
  const critical = workspaces.filter(
    (w) => w.riskLevel === "Critical" && w.status !== "Closed",
  ).length;

  // funds by destination entity type
  const entityCounts = ["vasp", "mixer", "bridge", "contract", "unknown"].map(
    (t) => ({
      type: t,
      count: workspaces.reduce(
        (s, w) => s + w.nodes.filter((n) => n.type === t).length,
        0,
      ),
    }),
  );
  const entityCfg = {
    count: { label: "Addresses" },
    vasp: { label: "Exchange / VASP", color: "#ef4444" },
    mixer: { label: "Mixer", color: "#a855f7" },
    bridge: { label: "Bridge", color: "#f59e0b" },
    contract: { label: "Contract", color: "#94a3b8" },
    unknown: { label: "Unidentified", color: "#3b82f6" },
  } satisfies ChartConfig;

  // most-hit exchanges
  const vaspHits: Record<string, number> = {};
  workspaces.forEach((w) =>
    w.nodes
      .filter((n) => n.type === "vasp")
      .forEach((n) => {
        vaspHits[n.label] = (vaspHits[n.label] ?? 0) + 1;
      }),
  );
  const vaspRows = Object.entries(vaspHits)
    .map(([name, hits]) => ({ name, hits }))
    .sort((a, b) => b.hits - a.hits)
    .slice(0, 6);

  const kpis = [
    {
      label: "Active cases",
      value: active.length,
      icon: FolderOpenIcon,
      note: `${workspaces.length} total workspaces`,
      badge: "+2 this week",
    },
    {
      label: "Critical cases",
      value: critical,
      icon: ShieldAlertIcon,
      note: "Score ≥ 75, needs action",
      badge: `${openAlerts.length} open alerts`,
      danger: true,
    },
    {
      label: "Funds traced",
      value: inr(traced),
      icon: BanknoteIcon,
      note: "Across all complaints",
      badge: "NCRP linked",
    },
    {
      label: "VASPs identified",
      value: vaspSet.size,
      icon: BuildingIcon,
      note: [...vaspSet].slice(0, 3).join(", ") || "—",
      badge: "Freeze-ready",
    },
  ];

  return (
    <>
      <div className="grid grid-cols-1 gap-4 *:data-[slot=card]:bg-linear-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label} className="@container/card">
            <CardHeader>
              <CardDescription>{k.label}</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                {k.value}
              </CardTitle>
              <CardAction>
                <Badge
                  variant="outline"
                  className={cn(k.danger && "border-red-500/40 text-red-400")}
                >
                  <k.icon />
                  {k.badge}
                </Badge>
              </CardAction>
            </CardHeader>
            <CardFooter className="text-sm text-muted-foreground">
              {k.note}
            </CardFooter>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 @4xl/main:grid-cols-3">
        <Card className="@4xl/main:col-span-2">
          <CardHeader>
            <CardTitle>Traces by risk level</CardTitle>
            <CardDescription>
              Complaints auto-traced per day, last 30 days
            </CardDescription>
            <CardAction>
              <Badge variant="outline">
                <TrendingUpIcon />
                +18% vs prev. 30d
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent>
            <ChartContainer
              config={trendCfg}
              className="aspect-auto h-[260px] w-full"
            >
              <AreaChart data={TREND}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  minTickGap={32}
                  tickFormatter={(v) =>
                    new Date(v).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                    })
                  }
                />
                <ChartTooltip
                  cursor={false}
                  content={<ChartTooltipContent indicator="dot" />}
                />
                {(["low", "medium", "high", "critical"] as const).map((k) => (
                  <Area
                    key={k}
                    dataKey={k}
                    type="monotone"
                    stackId="a"
                    fill={`var(--color-${k})`}
                    fillOpacity={0.5}
                    stroke={`var(--color-${k})`}
                  />
                ))}
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
                  {entityCounts.map((e) => (
                    <Cell key={e.type} fill={`var(--color-${e.type})`} />
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
            <ChartContainer
              config={{
                hits: { label: "Deposit addresses", color: "#ef4444" },
              }}
              className="aspect-auto h-[210px] w-full"
            >
              <BarChart data={vaspRows} layout="vertical" margin={{ left: 0 }}>
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
                className={buttonVariants({ variant: "ghost", size: "sm" })}
              >
                View all <ArrowUpRightIcon />
              </Link>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col divide-y">
            {alerts.slice(0, 4).map((a) => (
              <div
                key={a.id}
                className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0"
              >
                <RiskBadge level={a.level} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">{a.message}</p>
                  <p className="text-xs text-muted-foreground">
                    <Link
                      href={`/workspaces/${a.workspaceId}`}
                      className="underline-offset-2 hover:underline"
                    >
                      {a.workspaceId}
                    </Link>{" "}
                    · {fmtTime(a.at)}
                  </p>
                </div>
                {!a.acknowledged ? (
                  <Button
                    size="xs"
                    variant="outline"
                    onClick={() => dispatch({ type: "ack", alertId: a.id })}
                  >
                    Acknowledge
                  </Button>
                ) : (
                  <span className="text-xs text-muted-foreground">Ack’d</span>
                )}
              </div>
            ))}
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
              className={buttonVariants({ variant: "outline", size: "sm" })}
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
              {workspaces.slice(0, 5).map((w) => (
                <TableRow key={w.id}>
                  <TableCell>
                    <Link
                      href={`/workspaces/${w.id}`}
                      className="font-medium hover:underline"
                    >
                      {w.id}
                    </Link>
                    <div className="max-w-[260px] truncate text-xs text-muted-foreground">
                      {w.title}
                    </div>
                  </TableCell>
                  <TableCell>
                    <RiskBadge level={w.riskLevel} score={w.riskScore} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={w.status} />
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {inr(w.amountInr)}
                  </TableCell>
                  <TableCell className="text-xs">
                    {w.summary.vasps.join(", ") || (
                      <span className="text-muted-foreground">
                        Unattributed
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <MemberStack ids={w.members} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}
