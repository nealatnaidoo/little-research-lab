"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
    Plus,
    MoreHorizontal,
    Pencil,
    Trash2,
    Send,
    Clock,
    Loader2,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ContentService, ContentItemResponse } from "@/lib/api"

type ContentTier = "free" | "premium" | "subscriber_only"

const TIER_BADGES: Record<ContentTier, { label: string; className: string }> = {
    free: {
        label: "Free",
        className: "bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-300",
    },
    premium: {
        label: "Premium",
        className: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/20 dark:text-amber-400",
    },
    subscriber_only: {
        label: "Subscriber",
        className: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/20 dark:text-purple-400",
    },
}
import { AdminScheduleService } from "@/lib/api"
import { toast } from "sonner"

type StatusFilter = "all" | "draft" | "scheduled" | "published"

export default function ContentListPage() {
    const router = useRouter()
    const [items, setItems] = useState<ContentItemResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [publishingId, setPublishingId] = useState<string | null>(null)
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

    useEffect(() => {
        fetchContent()
    }, [])

    const fetchContent = async () => {
        try {
            const data = await ContentService.listContentApiContentGet()
            setItems(data)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load content")
        } finally {
            setLoading(false)
        }
    }

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to delete this content?")) return
        try {
            await ContentService.deleteContentApiContentItemIdDelete(id)
            toast.success("Content deleted")
            fetchContent()
        } catch (e) {
            console.error(e)
            toast.error("Delete failed")
        }
    }

    const handlePublishNow = async (id: string) => {
        try {
            setPublishingId(id)
            await AdminScheduleService.publishNowApiAdminSchedulePublishNowPost({ content_id: id })
            toast.success("Content published!")
            fetchContent()
        } catch (e) {
            console.error(e)
            toast.error("Failed to publish")
        } finally {
            setPublishingId(null)
        }
    }

    const filteredItems = items.filter((item) => {
        if (statusFilter === "all") return true
        return item.status === statusFilter
    })

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "published":
                return <Badge variant="success">Published</Badge>
            case "scheduled":
                return (
                    <Badge
                        variant="outline"
                        className="bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-800"
                    >
                        Scheduled
                    </Badge>
                )
            case "draft":
            default:
                return <Badge variant="secondary">Draft</Badge>
        }
    }

    const getTierBadge = (tier: string | undefined) => {
        const tierKey = (tier || "free") as ContentTier
        const config = TIER_BADGES[tierKey] || TIER_BADGES.free
        return (
            <Badge variant="outline" className={config.className}>
                {config.label}
            </Badge>
        )
    }

    const formatDate = (dateStr: string | null | undefined) => {
        if (!dateStr) return "-"
        const date = new Date(dateStr)
        return date.toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
        })
    }

    const statusCounts = {
        all: items.length,
        draft: items.filter((i) => i.status === "draft").length,
        scheduled: items.filter((i) => i.status === "scheduled").length,
        published: items.filter((i) => i.status === "published").length,
    }

    if (loading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Content</h1>
                <Button asChild>
                    <Link href="/admin/content/new">
                        <Plus className="mr-2 h-4 w-4" />
                        New Item
                    </Link>
                </Button>
            </div>

            <Tabs
                defaultValue="all"
                value={statusFilter}
                onValueChange={(v) => setStatusFilter(v as StatusFilter)}
            >
                <TabsList>
                    <TabsTrigger value="all">
                        All ({statusCounts.all})
                    </TabsTrigger>
                    <TabsTrigger value="draft">
                        Drafts ({statusCounts.draft})
                    </TabsTrigger>
                    <TabsTrigger value="scheduled">
                        Scheduled ({statusCounts.scheduled})
                    </TabsTrigger>
                    <TabsTrigger value="published">
                        Published ({statusCounts.published})
                    </TabsTrigger>
                </TabsList>
            </Tabs>

            <Card>
                <CardHeader>
                    <CardTitle>
                        {statusFilter === "all"
                            ? "All Items"
                            : statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Title</TableHead>
                                <TableHead>Slug</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Tier</TableHead>
                                <TableHead>Scheduled / Published</TableHead>
                                <TableHead className="w-[70px]"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredItems.length === 0 ? (
                                <TableRow>
                                    <TableCell
                                        colSpan={6}
                                        className="text-center text-muted-foreground h-24"
                                    >
                                        No content found.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredItems.map((item) => (
                                    <TableRow key={item.id}>
                                        <TableCell className="font-medium">
                                            <Link
                                                href={`/admin/content/${item.id}`}
                                                className="hover:underline"
                                            >
                                                {item.title}
                                            </Link>
                                        </TableCell>
                                        <TableCell className="text-muted-foreground">
                                            {item.slug}
                                        </TableCell>
                                        <TableCell>{getStatusBadge(item.status || "draft")}</TableCell>
                                        <TableCell>{getTierBadge(item.tier)}</TableCell>
                                        <TableCell>
                                            {item.status === "scheduled" && item.publish_at ? (
                                                <div className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400">
                                                    <Clock className="h-3 w-3" />
                                                    {formatDate(item.publish_at)}
                                                </div>
                                            ) : item.publish_at ? (
                                                <span className="text-sm text-muted-foreground">
                                                    {formatDate(item.publish_at)}
                                                </span>
                                            ) : (
                                                "-"
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button
                                                        variant="ghost"
                                                        className="h-8 w-8 p-0"
                                                    >
                                                        <span className="sr-only">Open menu</span>
                                                        <MoreHorizontal className="h-4 w-4" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                    <DropdownMenuItem
                                                        onClick={() =>
                                                            router.push(`/admin/content/${item.id}`)
                                                        }
                                                    >
                                                        <Pencil className="mr-2 h-4 w-4" />
                                                        Edit
                                                    </DropdownMenuItem>
                                                    {item.status === "draft" && (
                                                        <DropdownMenuItem
                                                            onClick={() => handlePublishNow(item.id)}
                                                            disabled={publishingId === item.id}
                                                        >
                                                            {publishingId === item.id ? (
                                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                            ) : (
                                                                <Send className="mr-2 h-4 w-4" />
                                                            )}
                                                            Publish Now
                                                        </DropdownMenuItem>
                                                    )}
                                                    <DropdownMenuSeparator />
                                                    <DropdownMenuItem
                                                        onClick={() => handleDelete(item.id)}
                                                        className="text-red-600 focus:text-red-600"
                                                    >
                                                        <Trash2 className="mr-2 h-4 w-4" />
                                                        Delete
                                                    </DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    )
}
