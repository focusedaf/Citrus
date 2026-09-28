"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { API_URL } from "@/lib/api"

export default function SettingsPage() {
  return (
    <Card className="max-w-2xl">
      <CardHeader><CardTitle>Settings</CardTitle><CardDescription>Prototype configuration</CardDescription></CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex justify-between"><span className="text-muted-foreground">Backend API</span><code>{API_URL}</code></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Complaint source</span><Badge variant="outline">NCRP / SAHYOG (mock)</Badge></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Chain</span><span>Ethereum (multi-chain planned)</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Risk model</span><span>Rule-based v1 (GNN planned)</span></div>
      </CardContent>
    </Card>
  )
}
