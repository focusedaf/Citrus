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
    <header
      className="
        sticky
        top-0
        z-30
        flex
        h-(--header-height)
        shrink-0
        items-center
        gap-2
        border-b
        border-cyan-400/[0.08]
        bg-[#030914]/70
        shadow-[0_8px_35px_rgba(0,0,0,0.28)]
        backdrop-blur-2xl
        supports-[backdrop-filter]:bg-[#030914]/55
      "
    >
      {/* subtle top highlight */}
      <div
        className="
          pointer-events-none
          absolute
          inset-x-0
          top-0
          h-px
          bg-gradient-to-r
          from-transparent
          via-cyan-400/20
          to-transparent
        "
      />

      <div className="flex w-full items-center gap-1 px-4 lg:gap-3 lg:px-6">
        <SidebarTrigger
          className="
            -ml-1
            rounded-lg
            border
            border-transparent
            p-1.5
            text-slate-500
            transition-all
            duration-200
            hover:border-cyan-400/15
            hover:bg-cyan-400/[0.06]
            hover:text-cyan-200
          "
        />

        <Separator
          orientation="vertical"
          className="
            mx-2
            h-4
            bg-cyan-400/[0.12]
            data-vertical:self-auto
          "
        />

        <div className="flex min-w-0 items-center">
          <h1
            className="
              flex
              items-center
              text-[15px]
              font-semibold
              tracking-tight
              text-slate-100
            "
          >
            {id && root === "workspaces" ? (
              <>
                <Link
                  href="/workspaces"
                  className="
                    rounded-md
                    px-1.5
                    py-0.5
                    text-slate-400
                    transition-colors
                    hover:bg-cyan-400/[0.05]
                    hover:text-cyan-300
                  "
                >
                  Workspaces
                </Link>

                <span className="mx-1.5 text-cyan-400/25">
                  /
                </span>

                <span
                  className="
                    rounded-md
                    bg-cyan-400/[0.035]
                    px-1.5
                    py-0.5
                    font-mono
                    text-[13px]
                    font-medium
                    text-cyan-300/90
                  "
                >
                  {id}
                </span>
              </>
            ) : (
              <span>{TITLES[root] ?? "Citrus"}</span>
            )}
          </h1>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <Badge
            variant="outline"
            className="
              hidden
              h-7
              gap-2
              rounded-full
              border-emerald-400/20
              bg-emerald-400/[0.045]
              px-2.5
              text-[11px]
              font-medium
              text-emerald-300
              shadow-[0_0_18px_rgba(16,185,129,0.07)]
              sm:flex
            "
          >
            <span
              className="
                size-1.5
                animate-pulse
                rounded-full
                bg-emerald-400
                shadow-[0_0_8px_rgba(52,211,153,0.8)]
              "
            />

            <span>Live</span>

            <span className="text-emerald-400/30">
              ·
            </span>

            <span className="text-emerald-300/75">
              Ethereum mainnet
            </span>
          </Badge>

          <button
            onClick={() => {
              if (confirm("Reset demo data to the seeded state?"))
                dispatch({ type: "reset" });
            }}
            className="
              rounded-lg
              border
              border-cyan-400/[0.10]
              bg-white/[0.025]
              px-2.5
              py-1.5
              text-[11px]
              font-medium
              text-slate-500
              shadow-[inset_0_1px_0_rgba(255,255,255,0.025)]
              transition-all
              duration-200
              hover:border-cyan-400/20
              hover:bg-cyan-400/[0.055]
              hover:text-cyan-200
              active:scale-[0.98]
            "
          >
            Reset demo
          </button>
        </div>
      </div>
    </header>
  );
}