"use client"

import { useEffect, useState } from "react"
import { format } from "date-fns"
import { Loader2, Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { AdminAuditService, type AuditEntryResponse } from "@/lib/api"

export default function AuditPage() {
    const [entries, setEntries] = useState<AuditEntryResponse[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(0)
    const limit = 20

    // Filters
    const [actionFilter, setActionFilter] = useState<string>("all")
    const [entityTypeFilter, setEntityTypeFilter] = useState<string>("all")

    useEffect(() => {
        fetchData()
    }, [page, actionFilter, entityTypeFilter])

    async function fetchData() {
        setLoading(true)
        try {
            const response = await AdminAuditService.queryAuditLogsApiAdminAuditGet(
                entityTypeFilter === "all" ? undefined : entityTypeFilter, // entityType
                undefined, // entityId
                undefined, // actorId
                actionFilter === "all" ? undefined : actionFilter, // action
                undefined, // start
                undefined, // end
                limit, // limit
                page * limit // offset
            )
            setEntries(response.items)
            setTotal(response.total)
        } catch (error) {
            console.error("Failed to fetch audit logs", error)
        } finally {
            setLoading(false)
        }
    }

    const actions = ["create", "update", "delete", "publish", "login", "view"] // Common actions
    const entityTypes = ["user", "content", "asset", "schedule", "settings"]

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Audit Log</h1>
                    <p className="text-muted-foreground">Track system activity and changes.</p>
                </div>
            </div>

            <div className="flex gap-4">
                <div className="w-[200px]">
                    <Select value={actionFilter} onValueChange={setActionFilter}>
                        <SelectTrigger>
                            <SelectValue placeholder="Filter by Action" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Actions</SelectItem>
                            {actions.map(a => (
                                <SelectItem key={a} value={a}>{a.toUpperCase()}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="w-[200px]">
                    <Select value={entityTypeFilter} onValueChange={setEntityTypeFilter}>
                        <SelectTrigger>
                            <SelectValue placeholder="Filter by Entity" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Entities</SelectItem>
                            {entityTypes.map(e => (
                                <SelectItem key={e} value={e}>{e.toUpperCase()}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <Card>
                <CardContent className="p-0">
                    <Table data-testid="audit-table">
                        <TableHeader>
                            <TableRow>
                                <TableHead>Timestamp</TableHead>
                                <TableHead>Action</TableHead>
                                <TableHead>Entity</TableHead>
                                <TableHead>Actor</TableHead>
                                <TableHead>Description</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="h-24 text-center">
                                        <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                                    </TableCell>
                                </TableRow>
                            ) : entries.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                                        No audit records found.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                entries.map((entry) => (
                                    <TableRow key={entry.id}>
                                        <TableCell className="whitespace-nowrap font-medium">
                                            {format(new Date(entry.timestamp), "MMM d, HH:mm:ss")}
                                        </TableCell>
                                        <TableCell>
                                            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold">
                                                {entry.action}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex flex-col">
                                                <span className="text-sm font-medium">{entry.entity_type}</span>
                                                <span className="text-xs text-muted-foreground truncate max-w-[100px]">{entry.entity_id}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <span className="text-sm">{entry.actor_name || "System"}</span>
                                        </TableCell>
                                        <TableCell className="max-w-[300px] truncate" title={entry.description}>
                                            {entry.description}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <div className="flex items-center justify-end gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0 || loading}
                >
                    Previous
                </Button>
                <span className="text-sm text-muted-foreground">
                    Page {page + 1} of {Math.ceil(total / limit) || 1}
                </span>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => p + 1)}
                    disabled={(page + 1) * limit >= total || loading}
                >
                    Next
                </Button>
            </div>
        </div>
    )
}
