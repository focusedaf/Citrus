"use client"

import * as React from "react"
import Link from "next/link"
import { CheckCheckIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Mono, RiskBadge } from "@/components/custom/bits"
import { fmtTime, short } from "@/lib/format"
import { useStore } from "@/lib/store"

export default function AlertsPage() {
  const { state, dispatch } = useStore()
  const [f, setF] = React.useState("open")
  const list = state.alerts.filter((a) => (f === "open" ? !a.acknowledged : f === "critical" ? a.level === "Critical" : true))
  return (
    <Card>
      <CardHeader>
        <CardTitle>Alerts</CardTitle>
        <CardDescription>Raised automatically when a trace scores High (≥50) or Critical (≥75)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <ToggleGroup value={[f]} onValueChange={(v) => v[0] && setF(v[0])} variant="outline" size="sm">
            <ToggleGroupItem value="open">Open</ToggleGroupItem>
            <ToggleGroupItem value="critical">Critical</ToggleGroupItem>
            <ToggleGroupItem value="all">All</ToggleGroupItem>
          </ToggleGroup>
          <Button size="sm" variant="outline" className="ml-auto" onClick={() => state.alerts.forEach((a) => !a.acknowledged && dispatch({ type: "ack", alertId: a.id }))}>
            <CheckCheckIcon />Acknowledge all
          </Button>
        </div>
        <Table>
          <TableHeader><TableRow><TableHead>Severity</TableHead><TableHead>Alert</TableHead><TableHead>Case</TableHead><TableHead>Wallet</TableHead><TableHead>Raised</TableHead><TableHead /></TableRow></TableHeader>
          <TableBody>
            {list.map((a) => (
              <TableRow key={a.id}>
                <TableCell><RiskBadge level={a.level} /></TableCell>
                <TableCell className="max-w-md whitespace-normal">{a.message}</TableCell>
                <TableCell><Link href={`/workspaces/${a.workspaceId}`} className="hover:underline">{a.workspaceId}</Link></TableCell>
                <TableCell><Mono>{short(a.address, 8, 6)}</Mono></TableCell>
                <TableCell className="whitespace-nowrap text-xs text-muted-foreground">{fmtTime(a.at)}</TableCell>
                <TableCell className="text-right">{a.acknowledged ? <span className="text-xs text-muted-foreground">Acknowledged</span> : <Button size="xs" variant="outline" onClick={() => dispatch({ type: "ack", alertId: a.id })}>Acknowledge</Button>}</TableCell>
              </TableRow>
            ))}
            {list.length === 0 && <TableRow><TableCell colSpan={6} className="py-10 text-center text-muted-foreground">All clear.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
