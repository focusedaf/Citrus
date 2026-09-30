"use client";

import * as React from "react";

import Link from "next/link";

import { PlusIcon, SearchIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Input } from "@/components/ui/input";

import { buttonVariants } from "@/components/ui/button";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  MemberStack,
  Mono,
  RiskBadge,
  StatusBadge,
} from "@/components/custom/bits";

import { fmtDate, inr, short } from "@/lib/format";

import { useStore } from "@/lib/store";

const STATUS_OPTIONS = [
  "All",
  "New",
  "Tracing",
  "In Review",
  "Freeze Requested",
  "Closed",
] as const;

type WorkspaceStatus = (typeof STATUS_OPTIONS)[number];

export default function WorkspacesPage() {
  const { state, ready } = useStore();

  const [q, setQ] = React.useState("");

  const [status, setStatus] =
    React.useState<WorkspaceStatus>("All");

  /*
   * Read the current status from the URL.
   *
   * This allows the sidebar to navigate to:
   * /workspaces?status=New
   * /workspaces?status=Tracing
   * /workspaces?status=In%20Review
   */
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlStatus = params.get("status");

    if (
      urlStatus &&
      STATUS_OPTIONS.includes(urlStatus as WorkspaceStatus)
    ) {
      setStatus(urlStatus as WorkspaceStatus);
    } else {
      setStatus("All");
    }
  }, []);

  /*
   * Listen for browser navigation / sidebar URL changes.
   *
   * This is useful when the sidebar changes the URL without
   * completely remounting the page.
   */
  React.useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const urlStatus = params.get("status");

      if (
        urlStatus &&
        STATUS_OPTIONS.includes(urlStatus as WorkspaceStatus)
      ) {
        setStatus(urlStatus as WorkspaceStatus);
      } else {
        setStatus("All");
      }
    };

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  /*
   * Change status from the dropdown.
   *
   * The Select component can return null, so the handler
   * explicitly accepts null.
   */
  const handleStatusChange = (
    value: WorkspaceStatus | null,
  ) => {
    if (!value) {
      return;
    }

    setStatus(value);

    const params = new URLSearchParams(
      window.location.search,
    );

    if (value === "All") {
      params.delete("status");
    } else {
      params.set("status", value);
    }

    const query = params.toString();

    const nextUrl = query
      ? `/workspaces?${query}`
      : "/workspaces";

    window.history.pushState({}, "", nextUrl);
  };

  /*
   * Filter directly from the current store state.
   *
   * Whenever StoreProvider updates state.workspaces,
   * this memo recalculates and the UI updates automatically.
   */
  const list = React.useMemo(() => {
    const search = q.trim().toLowerCase();

    return state.workspaces.filter((workspace) => {
      const matchesStatus =
        status === "All" ||
        workspace.status === status;

      if (!matchesStatus) {
        return false;
      }

      if (!search) {
        return true;
      }

      const searchableText = [
        workspace.id,
        workspace.title,
        workspace.address,
        workspace.complaintId,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableText.includes(search);
    });
  }, [state.workspaces, q, status]);

  return (
    <>
      {/* Search / filter toolbar */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="group relative w-full max-w-sm">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-cyan-400/55 transition-colors group-focus-within:text-cyan-300" />

          <Input
            value={q}
            onChange={(event) =>
              setQ(event.target.value)
            }
            placeholder="Search case, complaint ID or wallet…"
            className="
              h-10
              border-cyan-400/10
              bg-slate-950/55
              pl-9
              text-sm
              text-slate-200
              shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]
              backdrop-blur-xl
              placeholder:text-slate-500
              transition-all
              focus:border-cyan-400/35
              focus:bg-slate-950/75
              focus:ring-1
              focus:ring-cyan-400/15
              hover:border-cyan-400/20
            "
          />
        </div>

        <Select
          value={status}
          onValueChange={handleStatusChange}
        >
          <SelectTrigger
            className="
              h-10
              w-44
              border-cyan-400/10
              bg-slate-950/55
              text-slate-300
              shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]
              backdrop-blur-xl
              transition-all
              hover:border-cyan-400/20
              hover:bg-slate-900/65
              focus:border-cyan-400/30
              focus:ring-cyan-400/10
            "
          >
            <SelectValue />
          </SelectTrigger>

          <SelectContent
            className="
              border-cyan-400/15
              bg-[#08121f]/95
              text-slate-300
              shadow-2xl
              shadow-cyan-950/30
              backdrop-blur-2xl
            "
          >
            {STATUS_OPTIONS.map((option) => (
              <SelectItem
                key={option}
                value={option}
                className="
                  cursor-pointer
                  focus:bg-cyan-400/10
                  focus:text-cyan-200
                "
              >
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Link
          href="/trace"
          className={buttonVariants({
            className: `
              ml-auto
              h-10
              border
              border-cyan-300/20
              bg-gradient-to-r
              from-cyan-500
              via-sky-500
              to-blue-600
              px-4
              font-medium
              text-white
              shadow-[0_0_24px_rgba(14,165,233,0.16)]
              transition-all
              hover:border-cyan-200/35
              hover:from-cyan-400
              hover:via-sky-400
              hover:to-blue-500
              hover:shadow-[0_0_32px_rgba(14,165,233,0.28)]
              active:scale-[0.98]
            `,
          })}
        >
          <PlusIcon />
          New workspace
        </Link>
      </div>

      {!ready ? (
        <div
          className="
            rounded-2xl
            border
            border-cyan-400/10
            bg-slate-950/45
            px-6
            py-16
            text-center
            text-sm
            text-slate-500
            shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]
            backdrop-blur-xl
          "
        >
          Loading workspaces…
        </div>
      ) : (
        <div className="grid gap-5 @2xl/main:grid-cols-2 @5xl/main:grid-cols-3">
          {list.map((workspace) => (
            <Link
              key={workspace.id}
              href={`/workspaces/${workspace.id}`}
              className="group"
            >
              <Card
                className="
                  relative
                  h-full
                  overflow-hidden
                  border
                  border-cyan-400/[0.09]
                  bg-[linear-gradient(145deg,rgba(12,30,49,0.72),rgba(4,12,22,0.72))]
                  shadow-[0_18px_50px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.035)]
                  backdrop-blur-2xl
                  transition-all
                  duration-300
                  group-hover:-translate-y-1
                  group-hover:border-cyan-300/25
                  group-hover:shadow-[0_20px_60px_rgba(0,0,0,0.32),0_0_32px_rgba(14,165,233,0.07),inset_0_1px_0_rgba(255,255,255,0.05)]
                "
              >
                {/* Ambient card glow */}
                <div
                  className="
                    pointer-events-none
                    absolute
                    -top-24
                    -right-24
                    h-40
                    w-40
                    rounded-full
                    bg-cyan-400/[0.055]
                    blur-3xl
                    transition-all
                    duration-500
                    group-hover:bg-cyan-400/[0.10]
                  "
                />

                {/* Top accent */}
                <div
                  className="
                    absolute
                    top-0
                    left-0
                    h-px
                    w-0
                    bg-gradient-to-r
                    from-cyan-300
                    via-sky-400
                    to-transparent
                    transition-all
                    duration-500
                    group-hover:w-full
                  "
                />

                <CardHeader className="relative pb-4">
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className="
                        font-mono
                        text-[10px]
                        uppercase
                        tracking-[0.12em]
                        text-slate-500
                      "
                    >
                      {workspace.id} ·{" "}
                      {fmtDate(workspace.createdAt)}
                    </span>

                    <RiskBadge
                      level={workspace.riskLevel}
                      score={workspace.riskScore}
                    />
                  </div>

                  <CardTitle
                    className="
                      mt-1
                      leading-snug
                      text-[17px]
                      font-medium
                      text-slate-100
                      transition-colors
                      group-hover:text-cyan-50
                    "
                  >
                    {workspace.title}
                  </CardTitle>

                  <CardDescription
                    className="
                      flex
                      items-center
                      gap-1.5
                      text-slate-500
                    "
                  >
                    <Mono>
                      <span className="text-cyan-300/70">
                        {short(
                          workspace.address,
                          10,
                          6,
                        )}
                      </span>
                    </Mono>

                    <span className="text-slate-700">
                      ·
                    </span>

                    <span>
                      {workspace.victimState}
                    </span>
                  </CardDescription>
                </CardHeader>

                <CardContent className="relative space-y-4">
                  {/* Metrics */}
                  <div
                    className="
                      grid
                      grid-cols-3
                      divide-x
                      divide-cyan-400/[0.08]
                      overflow-hidden
                      rounded-xl
                      border
                      border-cyan-400/[0.07]
                      bg-slate-950/35
                    "
                  >
                    <div className="px-3 py-2.5">
                      <div className="text-[9px] uppercase tracking-[0.12em] text-slate-600">
                        Transactions
                      </div>

                      <div className="mt-1 font-mono text-sm text-slate-200">
                        {workspace.summary.transactions}
                      </div>
                    </div>

                    <div className="px-3 py-2.5">
                      <div className="text-[9px] uppercase tracking-[0.12em] text-slate-600">
                        Depth
                      </div>

                      <div className="mt-1 font-mono text-sm text-slate-200">
                        {workspace.summary.depth} hops
                      </div>
                    </div>

                    <div className="px-3 py-2.5">
                      <div className="text-[9px] uppercase tracking-[0.12em] text-slate-600">
                        Value
                      </div>

                      <div className="mt-1 truncate text-sm text-slate-200">
                        {inr(workspace.amountInr)}
                      </div>
                    </div>
                  </div>

                  {/* VASP / entity information */}
                  <div
                    className="
                      min-h-9
                      rounded-lg
                      border
                      border-cyan-400/[0.06]
                      bg-cyan-400/[0.018]
                      px-3
                      py-2.5
                      text-xs
                    "
                  >
                    {workspace.summary.vasps.length ? (
                      <>
                        <span className="text-slate-500">
                          Reached:{" "}
                        </span>

                        <b className="font-medium text-cyan-200/85">
                          {workspace.summary.vasps.join(
                            ", ",
                          )}
                        </b>
                      </>
                    ) : (
                      <span className="text-slate-600">
                        No exchange reached yet
                      </span>
                    )}
                  </div>
                </CardContent>

                <CardFooter
                  className="
                    relative
                    justify-between
                    border-t
                    border-cyan-400/[0.06]
                    bg-slate-950/20
                    px-6
                    py-3.5
                  "
                >
                  <StatusBadge
                    status={workspace.status}
                  />

                  <MemberStack
                    ids={workspace.members}
                  />
                </CardFooter>
              </Card>
            </Link>
          ))}

          {list.length === 0 && (
            <div
              className="
                col-span-full
                rounded-2xl
                border
                border-dashed
                border-cyan-400/10
                bg-slate-950/35
                px-6
                py-16
                text-center
                text-sm
                text-slate-500
                backdrop-blur-xl
              "
            >
              {status !== "All"
                ? `No ${status} workspaces found.`
                : "No workspaces match your search."}
            </div>
          )}
        </div>
      )}
    </>
  );
}