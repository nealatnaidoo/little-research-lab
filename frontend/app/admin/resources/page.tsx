"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
    Plus,
    MoreHorizontal,
    Pencil,
    Trash2,
    FileText,
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
import { AdminResourcesService, type ResourcePDFResponse } from "@/lib/api"
import { toast } from "sonner"

type StatusFilter = "all" | "draft" | "scheduled" | "published"

export default function ResourcesListPage() {
    const router = useRouter()
    const [items, setItems] = useState<ResourcePDFResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

    useEffect(() => {
        fetchResources()
    }, [])

    const fetchResources = async () => {
        try {
            const data = await AdminResourcesService.listResources()
            setItems(data)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load resources")
        } finally {
            setLoading(false)
        }
    }

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to delete this resource?")) return
        try {
            await AdminResourcesService.deleteResource(id)
            toast.success("Resource deleted")
            fetchResources()
        } catch (e) {
            console.error(e)
            toast.error("Delete failed")
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

    const getPolicyBadge = (policy: string) => {
        if (policy === "pinned") {
            return (
                <Badge variant="outline" className="text-amber-600 border-amber-300">
                    Pinned
                </Badge>
            )
        }
        return (
            <Badge variant="outline" className="text-green-600 border-green-300">
                Latest
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
                <div className="flex items-center gap-3">
                    <FileText className="h-8 w-8 text-muted-foreground" />
                    <h1 className="text-3xl font-bold tracking-tight">PDF Resources</h1>
                </div>
                <Button asChild>
                    <Link href="/admin/resources/new">
                        <Plus className="mr-2 h-4 w-4" />
                        New Resource
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
                            ? "All Resources"
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
                                <TableHead>Policy</TableHead>
                                <TableHead>Updated</TableHead>
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
                                        No resources found. Create your first PDF resource!
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredItems.map((item) => (
                                    <TableRow key={item.id}>
                                        <TableCell className="font-medium">
                                            <Link
                                                href={`/admin/resources/${item.id}`}
                                                className="hover:underline"
                                            >
                                                {item.title}
                                            </Link>
                                        </TableCell>
                                        <TableCell className="text-muted-foreground">
                                            /r/{item.slug}
                                        </TableCell>
                                        <TableCell>{getStatusBadge(item.status || "draft")}</TableCell>
                                        <TableCell>{getPolicyBadge(item.pinned_policy)}</TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {formatDate(item.updated_at)}
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
                                                            router.push(`/admin/resources/${item.id}`)
                                                        }
                                                    >
                                                        <Pencil className="mr-2 h-4 w-4" />
                                                        Edit
                                                    </DropdownMenuItem>
                                                    {item.status === "published" && (
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                window.open(`/r/${item.slug}`, "_blank")
                                                            }
                                                        >
                                                            <FileText className="mr-2 h-4 w-4" />
                                                            View Public
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
