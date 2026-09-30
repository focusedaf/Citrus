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
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              render={<Link href="/dashboard" />}
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-amber-400 text-lg text-black">
                🍋
              </div>

              <div className="grid flex-1 text-left leading-tight">
                <span className="text-base font-semibold">
                  Citrus
                </span>

                <span className="text-[11px] text-muted-foreground">
                  Crypto Fraud Attribution
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent className="flex flex-col gap-2">
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  tooltip="New investigation"
                  render={<Link href="/trace" />}
                  className="min-w-8 bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"
                >
                  <RadarIcon />
                  <span>New Investigation</span>
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
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>

                  {typeof item.badge === "number" &&
                    item.badge > 0 && (
                      <SidebarMenuBadge>
                        {item.badge}
                      </SidebarMenuBadge>
                    )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>
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
                      >
                        <SearchCheckIcon />

                        <span className="truncate">
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

        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  tooltip="Settings"
                  isActive={isActive("/settings")}
                  render={
                    <Link href="/settings" />
                  }
                >
                  <Settings2Icon />
                  <span>Settings</span>
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  tooltip="Help"
                  render={
                    <Link href="/settings" />
                  }
                >
                  <CircleHelpIcon />
                  <span>Help</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
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