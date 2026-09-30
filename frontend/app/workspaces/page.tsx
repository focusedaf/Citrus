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
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-sm">
          <SearchIcon className="absolute top-2.5 left-2.5 size-4 text-muted-foreground" />

          <Input
            value={q}
            onChange={(event) =>
              setQ(event.target.value)
            }
            placeholder="Search case, complaint ID or wallet…"
            className="pl-8"
          />
        </div>

        <Select
          value={status}
          onValueChange={handleStatusChange}
        >
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>

          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem
                key={option}
                value={option}
              >
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Link
          href="/trace"
          className={buttonVariants({
            className: "ml-auto",
          })}
        >
          <PlusIcon />
          New workspace
        </Link>
      </div>

      {!ready ? (
        <div className="py-12 text-center text-sm text-muted-foreground">
          Loading workspaces…
        </div>
      ) : (
        <div className="grid gap-4 @2xl/main:grid-cols-2 @5xl/main:grid-cols-3">
          {list.map((workspace) => (
            <Link
              key={workspace.id}
              href={`/workspaces/${workspace.id}`}
              className="group"
            >
              <Card className="h-full transition-colors group-hover:border-primary/40">
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted-foreground">
                      {workspace.id} ·{" "}
                      {fmtDate(workspace.createdAt)}
                    </span>

                    <RiskBadge
                      level={workspace.riskLevel}
                      score={workspace.riskScore}
                    />
                  </div>

                  <CardTitle className="leading-snug">
                    {workspace.title}
                  </CardTitle>

                  <CardDescription>
                    <Mono>
                      {short(
                        workspace.address,
                        10,
                        6,
                      )}
                    </Mono>

                    {" · "}

                    {workspace.victimState}
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>
                      {workspace.summary.transactions} txns
                    </span>

                    <span>
                      {workspace.summary.depth} hops
                    </span>

                    <span>
                      {inr(workspace.amountInr)}
                    </span>
                  </div>

                  <div className="text-xs">
                    {workspace.summary.vasps.length ? (
                      <>
                        Reached:{" "}
                        <b>
                          {workspace.summary.vasps.join(
                            ", ",
                          )}
                        </b>
                      </>
                    ) : (
                      <span className="text-muted-foreground">
                        No exchange reached yet
                      </span>
                    )}
                  </div>
                </CardContent>

                <CardFooter className="justify-between">
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
            <div className="col-span-full py-12 text-center text-sm text-muted-foreground">
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