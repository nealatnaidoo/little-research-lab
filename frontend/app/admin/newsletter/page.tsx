"use client"

import { useEffect, useState } from "react"
import { Download, Loader2, RefreshCw, Trash2, Users } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { OpenAPI } from "@/lib/api"

// Types for newsletter API
interface Subscriber {
    id: string
    email: string
    status: "pending" | "confirmed" | "unsubscribed"
    created_at: string
    confirmed_at: string | null
    unsubscribed_at: string | null
}

interface SubscriberListResponse {
    subscribers: Subscriber[]
    total: number
    offset: number
    limit: number
}

interface NewsletterStats {
    total: number
    pending: number
    confirmed: number
    unsubscribed: number
}

// API helper functions
async function fetchWithAuth(url: string, options: RequestInit = {}) {
    const baseUrl = OpenAPI.BASE || "http://localhost:8000"
    const headers: HeadersInit = {
        "Content-Type": "application/json",
        ...options.headers,
    }

    // Add auth token from cookie or storage
    const response = await fetch(`${baseUrl}${url}`, {
        ...options,
        headers,
        credentials: "include",
    })

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
    }

    return response
}

async function getSubscribers(
    status?: string,
    offset: number = 0,
    limit: number = 50
): Promise<SubscriberListResponse> {
    const params = new URLSearchParams()
    if (status && status !== "all") params.set("status", status)
    params.set("offset", offset.toString())
    params.set("limit", limit.toString())

    const response = await fetchWithAuth(
        `/api/admin/newsletter/subscribers?${params.toString()}`
    )
    return response.json()
}

async function deleteSubscriber(id: string): Promise<void> {
    await fetchWithAuth(`/api/admin/newsletter/subscribers/${id}`, {
        method: "DELETE",
    })
}

async function getStats(): Promise<NewsletterStats> {
    const response = await fetchWithAuth("/api/admin/newsletter/stats")
    return response.json()
}

async function exportCsv(status?: string): Promise<void> {
    const baseUrl = OpenAPI.BASE || "http://localhost:8000"
    const params = new URLSearchParams()
    if (status && status !== "all") params.set("status", status)

    // Open CSV download in new tab (browser will handle download)
    window.open(
        `${baseUrl}/api/admin/newsletter/subscribers/export/csv?${params.toString()}`,
        "_blank"
    )
}

export default function NewsletterPage() {
    const [subscribers, setSubscribers] = useState<Subscriber[]>([])
    const [stats, setStats] = useState<NewsletterStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [total, setTotal] = useState(0)
    const [offset, setOffset] = useState(0)
    const [statusFilter, setStatusFilter] = useState<string>("all")
    const [deleteId, setDeleteId] = useState<string | null>(null)
    const [deleteEmail, setDeleteEmail] = useState<string>("")
    const limit = 50

    useEffect(() => {
        fetchData()
    }, [statusFilter, offset])

    async function fetchData() {
        setLoading(true)
        try {
            const [listData, statsData] = await Promise.all([
                getSubscribers(statusFilter, offset, limit),
                getStats(),
            ])
            setSubscribers(listData.subscribers)
            setTotal(listData.total)
            setStats(statsData)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load subscribers")
        } finally {
            setLoading(false)
        }
    }

    async function handleDelete() {
        if (!deleteId) return
        try {
            await deleteSubscriber(deleteId)
            toast.success("Subscriber deleted")
            setDeleteId(null)
            setDeleteEmail("")
            fetchData()
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete subscriber")
        }
    }

    function openDeleteDialog(id: string, email: string) {
        setDeleteId(id)
        setDeleteEmail(email)
    }

    function handleExport() {
        exportCsv(statusFilter)
        toast.success("CSV export started")
    }

    function formatDate(dateStr: string | null) {
        if (!dateStr) return "-"
        return new Date(dateStr).toLocaleDateString("en-GB", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        })
    }

    function getStatusBadge(status: string) {
        switch (status) {
            case "confirmed":
                return <Badge variant="default">Confirmed</Badge>
            case "pending":
                return <Badge variant="secondary">Pending</Badge>
            case "unsubscribed":
                return <Badge variant="outline">Unsubscribed</Badge>
            default:
                return <Badge variant="outline">{status}</Badge>
        }
    }

    const totalPages = Math.ceil(total / limit)
    const currentPage = Math.floor(offset / limit) + 1

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Newsletter</h1>
                    <p className="text-muted-foreground">
                        Manage newsletter subscribers and subscriptions.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={handleExport}>
                        <Download className="mr-2 h-4 w-4" />
                        Export CSV
                    </Button>
                    <Button variant="outline" onClick={fetchData}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Refresh
                    </Button>
                </div>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid gap-4 md:grid-cols-4">
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Total Subscribers</CardDescription>
                            <CardTitle className="text-2xl">{stats.total}</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Confirmed</CardDescription>
                            <CardTitle className="text-2xl text-green-600">
                                {stats.confirmed}
                            </CardTitle>
                        </CardHeader>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Pending</CardDescription>
                            <CardTitle className="text-2xl text-yellow-600">
                                {stats.pending}
                            </CardTitle>
                        </CardHeader>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Unsubscribed</CardDescription>
                            <CardTitle className="text-2xl text-muted-foreground">
                                {stats.unsubscribed}
                            </CardTitle>
                        </CardHeader>
                    </Card>
                </div>
            )}

            {/* Filters */}
            <div className="flex gap-4 items-center">
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Filter by status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                        <SelectItem value="confirmed">Confirmed</SelectItem>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="unsubscribed">Unsubscribed</SelectItem>
                    </SelectContent>
                </Select>
                <span className="text-sm text-muted-foreground">
                    Showing {subscribers.length} of {total} subscribers
                </span>
            </div>

            {/* Subscribers Table */}
            <Card>
                <CardContent className="p-0">
                    <Table data-testid="newsletter-table">
                        <TableHeader>
                            <TableRow>
                                <TableHead>Email</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Subscribed</TableHead>
                                <TableHead>Confirmed</TableHead>
                                <TableHead className="w-[100px]"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="h-24 text-center">
                                        <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                                    </TableCell>
                                </TableRow>
                            ) : subscribers.length === 0 ? (
                                <TableRow>
                                    <TableCell
                                        colSpan={5}
                                        className="h-24 text-center text-muted-foreground"
                                    >
                                        <Users className="mx-auto h-8 w-8 mb-2 opacity-50" />
                                        No subscribers found.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                subscribers.map((subscriber) => (
                                    <TableRow key={subscriber.id}>
                                        <TableCell className="font-medium">
                                            {subscriber.email}
                                        </TableCell>
                                        <TableCell>{getStatusBadge(subscriber.status)}</TableCell>
                                        <TableCell className="text-muted-foreground">
                                            {formatDate(subscriber.created_at)}
                                        </TableCell>
                                        <TableCell className="text-muted-foreground">
                                            {formatDate(subscriber.confirmed_at)}
                                        </TableCell>
                                        <TableCell>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="text-destructive"
                                                onClick={() =>
                                                    openDeleteDialog(subscriber.id, subscriber.email)
                                                }
                                                title="Delete subscriber (GDPR)"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">
                        Page {currentPage} of {totalPages}
                    </span>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            disabled={offset === 0}
                            onClick={() => setOffset(Math.max(0, offset - limit))}
                        >
                            Previous
                        </Button>
                        <Button
                            variant="outline"
                            disabled={offset + limit >= total}
                            onClick={() => setOffset(offset + limit)}
                        >
                            Next
                        </Button>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Dialog */}
            <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Subscriber?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete <strong>{deleteEmail}</strong> and all
                            associated data. This action cannot be undone (GDPR right to erasure).
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Delete Permanently
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}
