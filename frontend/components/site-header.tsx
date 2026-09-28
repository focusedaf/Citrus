"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { useStore } from "@/lib/store";

const TITLES: Record<string, string> = {
  dashboard: "Dashboard",
  workspaces: "Workspaces",
  alerts: "Alerts",
  reports: "Reports",
  trace: "New Investigation",
  settings: "Settings",
};

export function SiteHeader() {
  const path = usePathname();
  const { dispatch } = useStore();
  const [root, id] = path.split("/").filter(Boolean);
  return (
    <header className="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 h-4 data-vertical:self-auto"
        />
        <h1 className="text-base font-medium">
          {id && root === "workspaces" ? (
            <>
              <Link
                href="/workspaces"
                className="text-muted-foreground hover:text-foreground"
              >
                Workspaces
              </Link>
              <span className="mx-1.5 text-muted-foreground">/</span>
              {id}
            </>
          ) : (
            (TITLES[root] ?? "Citrus")
          )}
        </h1>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="outline" className="gap-1.5">
            <span className="size-1.5 animate-pulse rounded-full bg-emerald-400" />
            Live · Ethereum mainnet
          </Badge>
          <button
            onClick={() => {
              if (confirm("Reset demo data to the seeded state?"))
                dispatch({ type: "reset" });
            }}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Reset demo
          </button>
        </div>
      </div>
    </header>
  );
}
