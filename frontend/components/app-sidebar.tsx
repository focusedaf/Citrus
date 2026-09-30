"use client";

import * as React from "react";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NavUser } from "@/components/nav-user";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

import { useStore } from "@/lib/store";
import { getReports } from "@/lib/api";

import {
  BellRingIcon,
  CircleHelpIcon,
  FileChartColumnIcon,
  FolderKanbanIcon,
  LayoutDashboardIcon,
  RadarIcon,
  SearchCheckIcon,
  Settings2Icon,
} from "lucide-react";

export function AppSidebar(
  props: React.ComponentProps<typeof Sidebar>,
) {
  const pathname = usePathname() ?? "";
  const { state } = useStore();
  const [reportCount, setReportCount] = React.useState(0);

  /*
   * Backend data can occasionally contain incomplete workspace records.
   * Keep the sidebar defensive so one malformed record cannot crash
   * the entire application.
   */
  const workspaces = Array.isArray(state.workspaces)
    ? state.workspaces
    : [];

  const alerts = Array.isArray(state.alerts)
    ? state.alerts
    : [];

  const openAlerts = alerts.filter(
    (alert) => !alert.acknowledged,
  ).length;

  const activeCases = workspaces.filter(
    (workspace) => workspace?.status !== "Closed",
  ).length;

  /*
   * Reports are not currently stored in the global store, so the
   * sidebar gets the current report count directly from the backend.
   */
  React.useEffect(() => {
    let cancelled = false;

    async function loadReportCount() {
      try {
        const reports = await getReports(500);

        if (!cancelled) {
          setReportCount(
            Array.isArray(reports) ? reports.length : 0,
          );
        }
      } catch (error) {
        console.error(
          "Failed to load report count:",
          error,
        );

        if (!cancelled) {
          setReportCount(0);
        }
      }
    }

    loadReportCount();

    return () => {
      cancelled = true;
    };
  }, [workspaces.length]);

  const main = [
    {
      title: "Dashboard",
      url: "/dashboard",
      icon: LayoutDashboardIcon,
    },
    {
      title: "Workspaces",
      url: "/workspaces",
      icon: FolderKanbanIcon,
      badge: activeCases,
    },
    {
      title: "Alerts",
      url: "/alerts",
      icon: BellRingIcon,
      badge: openAlerts,
    },
    {
      title: "Reports",
      url: "/reports",
      icon: FileChartColumnIcon,
      badge: reportCount,
    },
  ];

  const isActive = (url: string) =>
    pathname === url ||
    pathname.startsWith(`${url}/`);

  return (
    <Sidebar
      collapsible="offcanvas"
      {...props}
    >
      <SidebarHeader className="px-3 pt-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              render={<Link href="/dashboard" />}
              className="
                group
                relative
                h-[58px]
                rounded-xl
                border border-transparent
                px-2.5
                transition-all
                duration-200
                hover:border-cyan-400/10
                hover:bg-cyan-400/[0.035]
              "
            >
              <div
                className="
                  relative
                  flex
                  size-9
                  shrink-0
                  items-center
                  justify-center
                  overflow-hidden
                  rounded-xl
                  bg-gradient-to-br
                  from-amber-300
                  via-yellow-400
                  to-orange-400
                  text-lg
                  shadow-[0_0_22px_rgba(251,191,36,0.16)]
                  ring-1
                  ring-white/10
                "
              >
                <span className="relative z-10">🍋</span>

                <div
                  className="
                    absolute
                    inset-0
                    bg-gradient-to-br
                    from-white/25
                    via-transparent
                    to-transparent
                  "
                />
              </div>

              <div className="grid min-w-0 flex-1 text-left leading-tight">
                <span
                  className="
                    text-[15px]
                    font-semibold
                    tracking-tight
                    text-slate-100
                  "
                >
                  Citrus
                </span>

                <span
                  className="
                    mt-0.5
                    truncate
                    text-[10px]
                    font-medium
                    tracking-[0.02em]
                    text-slate-500
                  "
                >
                  Crypto Fraud Attribution
                </span>
              </div>

              <div
                className="
                  absolute
                  right-2
                  top-2
                  size-1.5
                  rounded-full
                  bg-cyan-400/70
                  shadow-[0_0_8px_rgba(34,211,238,0.6)]
                  opacity-0
                  transition-opacity
                  group-hover:opacity-100
                "
              />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="px-2">
        <SidebarGroup className="pt-4">
          <SidebarGroupContent className="flex flex-col gap-3">
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  tooltip="New investigation"
                  render={<Link href="/trace" />}
                  className="
                    relative
                    min-w-8
                    overflow-hidden
                    rounded-xl
                    border
                    border-cyan-300/20
                    bg-gradient-to-r
                    from-cyan-500
                    via-sky-500
                    to-blue-500
                    text-white
                    shadow-[0_0_24px_rgba(14,165,233,0.16)]
                    transition-all
                    duration-200
                    hover:border-cyan-200/30
                    hover:brightness-110
                    hover:shadow-[0_0_30px_rgba(14,165,233,0.25)]
                  "
                >
                  <div
                    className="
                      pointer-events-none
                      absolute
                      inset-0
                      bg-gradient-to-r
                      from-white/10
                      via-transparent
                      to-transparent
                    "
                  />

                  <RadarIcon className="relative size-[17px]" />

                  <span className="relative font-semibold">
                    New Investigation
                  </span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>

            <SidebarMenu>
              {main.map((item) => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton
                    tooltip={item.title}
                    isActive={isActive(item.url)}
                    render={<Link href={item.url} />}
                    className="
                      group
                      relative
                      h-9
                      rounded-lg
                      text-slate-400
                      transition-all
                      duration-200
                      hover:bg-cyan-400/[0.055]
                      hover:text-slate-200
                    "
                  >
                    <item.icon
                      className="
                        size-[17px]
                        transition-colors
                        group-hover:text-cyan-300
                      "
                    />

                    <span className="font-medium">
                      {item.title}
                    </span>
                  </SidebarMenuButton>

                  {typeof item.badge === "number" &&
                    item.badge > 0 && (
                      <SidebarMenuBadge
                        className="
                          right-2
                          rounded-md
                          border
                          border-cyan-400/10
                          bg-cyan-400/[0.055]
                          px-1.5
                          text-[10px]
                          font-semibold
                          text-slate-400
                        "
                      >
                        {item.badge}
                      </SidebarMenuBadge>
                    )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="pt-1">
          <SidebarGroupLabel
            className="
              px-2
              pb-2
              text-[10px]
              font-semibold
              uppercase
              tracking-[0.12em]
              text-slate-600
            "
          >
            Recent workspaces
          </SidebarGroupLabel>

          <SidebarGroupContent>
            <SidebarMenu>
              {workspaces
                .slice(0, 4)
                .map((workspace, index) => {
                  /*
                   * Some backend workspace records may currently be
                   * missing id/title. Never allow that to break the
                   * sidebar.
                   */
                  const workspaceId = String(
                    workspace?.id ??
                      workspace?.traceId ??
                      `workspace-${index}`,
                  );

                  const workspaceTitle = String(
                    workspace?.title ??
                      "Untitled workspace",
                  );

                  /*
                   * Index is included as the final fallback so even
                   * duplicate/malformed backend records cannot produce
                   * duplicate React keys.
                   */
                  const workspaceKey = `${workspaceId}-${workspace?.traceId ?? "unknown"}-${index}`;

                  const workspaceLabel =
                    workspaceTitle
                      .split("–")[0]
                      .trim() ||
                    workspaceTitle;

                  return (
                    <SidebarMenuItem
                      key={workspaceKey}
                    >
                      <SidebarMenuButton
                        tooltip={workspaceLabel}
                        isActive={
                          pathname ===
                          `/workspaces/${workspaceId}`
                        }
                        render={
                          <Link
                            href={`/workspaces/${workspaceId}`}
                          />
                        }
                        className="
                          group
                          h-9
                          rounded-lg
                          text-slate-400
                          transition-all
                          duration-200
                          hover:bg-cyan-400/[0.045]
                          hover:text-slate-200
                        "
                      >
                        <SearchCheckIcon
                          className="
                            size-[16px]
                            text-slate-500
                            transition-colors
                            group-hover:text-cyan-300
                          "
                        />

                        <span className="truncate text-[12px] font-medium">
                          {workspaceId} ·{" "}
                          {workspaceLabel}
                        </span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}

              {workspaces.length === 0 && (
                <SidebarMenuItem>
                  <SidebarMenuButton
                    disabled
                    className="text-muted-foreground"
                  >
                    <SearchCheckIcon />
                    <span>No recent workspaces</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-auto pb-2">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  tooltip="Settings"
                  isActive={isActive("/settings")}
                  render={
                    <Link href="/settings" />
                  }
                  className="
                    h-9
                    rounded-lg
                    text-slate-400
                    hover:bg-cyan-400/[0.045]
                    hover:text-slate-200
                  "
                >
                  <Settings2Icon className="size-[17px]" />
                  <span className="font-medium">
                    Settings
                  </span>
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  tooltip="Help"
                  render={
                    <Link href="/settings" />
                  }
                  className="
                    h-9
                    rounded-lg
                    text-slate-400
                    hover:bg-cyan-400/[0.045]
                    hover:text-slate-200
                  "
                >
                  <CircleHelpIcon className="size-[17px]" />
                  <span className="font-medium">
                    Help
                  </span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-cyan-400/[0.06] px-2 py-2">
        <NavUser
          user={{
            name: "Insp. Aarav Mehta",
            email:
              "aarav.mehta@cybercell.gov.in",
            avatar: "",
          }}
        />
      </SidebarFooter>
    </Sidebar>
  );
}