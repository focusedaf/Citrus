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
  Settings2Icon,
  SearchCheckIcon,
} from "lucide-react";

export function AppSidebar(props: React.ComponentProps<typeof Sidebar>) {
  const path = usePathname();
  const { state } = useStore();
  const [reportCount, setReportCount] = React.useState(0);

  const openAlerts = state.alerts.filter((a) => !a.acknowledged).length;
  const activeCases = state.workspaces.filter(
    (w) => w.status !== "Closed",
  ).length;

  React.useEffect(() => {
    let cancelled = false;

    async function loadReportCount() {
      try {
        const reports = await getReports(500);

        if (!cancelled) {
          setReportCount(reports.length);
        }
      } catch {
        if (!cancelled) {
          setReportCount(0);
        }
      }
    }

    loadReportCount();

    return () => {
      cancelled = true;
    };
  }, [state.workspaces.length]);

  const main = [
    { title: "Dashboard", url: "/dashboard", icon: LayoutDashboardIcon },
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

  const isActive = (u: string) => path === u || path.startsWith(u + "/");

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/dashboard" />}>
              <div className="flex size-8 items-center justify-center rounded-lg bg-amber-400 text-lg text-black">
                🍋
              </div>
              <div className="grid flex-1 text-left leading-tight">
                <span className="text-base font-semibold">Citrus</span>
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
              {main.map((it) => (
                <SidebarMenuItem key={it.title}>
                  <SidebarMenuButton
                    tooltip={it.title}
                    isActive={isActive(it.url)}
                    render={<Link href={it.url} />}
                  >
                    <it.icon />
                    <span>{it.title}</span>
                  </SidebarMenuButton>

                  {!!it.badge && (
                    <SidebarMenuBadge>{it.badge}</SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Recent workspaces</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {state.workspaces.slice(0, 4).map((w) => (
                <SidebarMenuItem key={w.id}>
                  <SidebarMenuButton
                    isActive={path === `/workspaces/${w.id}`}
                    render={<Link href={`/workspaces/${w.id}`} />}
                  >
                    <SearchCheckIcon />
                    <span className="truncate">
                      {w.id} · {w.title.split("–")[0].trim()}
                    </span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton render={<Link href="/settings" />}>
                  <Settings2Icon />
                  <span>Settings</span>
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton render={<Link href="/settings" />}>
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
            email: "aarav.mehta@cybercell.gov.in",
            avatar: "",
          }}
        />
      </SidebarFooter>
    </Sidebar>
  );
}
