"use client"

import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2, Plus, Pencil, Trash2 } from "lucide-react"
import { toast } from "sonner"

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
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { AdminLinksService, type LinkResponse, LinkCreateRequest } from "@/lib/api"

const formSchema = z.object({
    title: z.string().min(1, "Title is required"),
    slug: z.string().min(1, "Slug is required"),
    url: z.string().url("Must be a valid URL"),
    icon: z.string().optional(),
    status: z.enum(["active", "disabled"]),
    position: z.number().int().min(0),
    visibility: z.enum(["public", "unlisted", "private"]),
})

type FormData = z.infer<typeof formSchema>

export default function LinksPage() {
    const [links, setLinks] = useState<LinkResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [dialogOpen, setDialogOpen] = useState(false)
    const [editingId, setEditingId] = useState<string | null>(null)

    const form = useForm<FormData>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            title: "",
            slug: "",
            url: "",
            icon: "",
            status: "active",
            position: 0,
            visibility: "public",
        },
    })

    useEffect(() => {
        fetchLinks()
    }, [])

    async function fetchLinks() {
        setLoading(true)
        try {
            const data = await AdminLinksService.listLinksApiAdminLinksGet()
            setLinks(data.items)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load links")
        } finally {
            setLoading(false)
        }
    }

    async function onSubmit(values: FormData) {
        try {
            if (editingId) {
                await AdminLinksService.updateLinkApiAdminLinksLinkIdPut(editingId, {
                    title: values.title,
                    slug: values.slug,
                    url: values.url,
                    icon: values.icon || null,
                    status: values.status === "active" ? LinkCreateRequest.status.ACTIVE : LinkCreateRequest.status.DISABLED,
                    position: values.position,
                    visibility: values.visibility === "public" ? LinkCreateRequest.visibility.PUBLIC : values.visibility === "unlisted" ? LinkCreateRequest.visibility.UNLISTED : LinkCreateRequest.visibility.PRIVATE,
                    group_id: null,
                })
                toast.success("Link updated")
            } else {
                await AdminLinksService.createLinkApiAdminLinksPost({
                    title: values.title,
                    slug: values.slug,
                    url: values.url,
                    icon: values.icon || null,
                    status: values.status === "active" ? LinkCreateRequest.status.ACTIVE : LinkCreateRequest.status.DISABLED,
                    position: values.position,
                    visibility: values.visibility === "public" ? LinkCreateRequest.visibility.PUBLIC : values.visibility === "unlisted" ? LinkCreateRequest.visibility.UNLISTED : LinkCreateRequest.visibility.PRIVATE,
                    group_id: null,
                })
                toast.success("Link created")
            }
            setDialogOpen(false)
            fetchLinks()
        } catch (error) {
            console.error(error)
            toast.error("Operation failed")
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Are you sure you want to delete this link?")) return
        try {
            await AdminLinksService.deleteLinkApiAdminLinksLinkIdDelete(id)
            toast.success("Link deleted")
            fetchLinks()
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete")
        }
    }

    function openCreate() {
        setEditingId(null)
        form.reset({
            title: "",
            slug: "",
            url: "",
            icon: "",
            status: "active",
            position: 0,
            visibility: "public",
        })
        setDialogOpen(true)
    }

    function openEdit(link: LinkResponse) {
        setEditingId(link.id)
        form.reset({
            title: link.title,
            slug: link.slug,
            url: link.url,
            icon: link.icon || "",
            status: link.status,
            position: link.position,
            visibility: link.visibility,
        })
        setDialogOpen(true)
    }

    const getStatusBadge = (status: string) => {
        return status === "active" ? (
            <Badge variant="success">Active</Badge>
        ) : (
            <Badge variant="secondary">Disabled</Badge>
        )
    }

    const getVisibilityBadge = (visibility: string) => {
        switch (visibility) {
            case "public":
                return <Badge variant="outline">Public</Badge>
            case "unlisted":
                return <Badge variant="outline">Unlisted</Badge>
            case "private":
                return <Badge variant="secondary">Private</Badge>
            default:
                return <Badge variant="outline">{visibility}</Badge>
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Links</h1>
                    <p className="text-muted-foreground">Manage navigation and social links.</p>
                </div>
                <Button onClick={openCreate}>
                    <Plus className="mr-2 h-4 w-4" />
                    New Link
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>All Links</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Title</TableHead>
                                <TableHead>URL</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Visibility</TableHead>
                                <TableHead>Position</TableHead>
                                <TableHead className="w-[100px]"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-24 text-center">
                                        <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                                    </TableCell>
                                </TableRow>
                            ) : links.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                                        No links found.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                links.map((link) => (
                                    <TableRow key={link.id}>
                                        <TableCell className="font-medium">
                                            {link.icon && <span className="mr-2">{link.icon}</span>}
                                            {link.title}
                                        </TableCell>
                                        <TableCell className="max-w-[300px] truncate">
                                            <a
                                                href={link.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-blue-600 hover:underline dark:text-blue-400"
                                            >
                                                {link.url}
                                            </a>
                                        </TableCell>
                                        <TableCell>{getStatusBadge(link.status)}</TableCell>
                                        <TableCell>{getVisibilityBadge(link.visibility)}</TableCell>
                                        <TableCell>{link.position}</TableCell>
                                        <TableCell>
                                            <div className="flex justify-end gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => openEdit(link)}
                                                >
                                                    <Pencil className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="text-destructive"
                                                    onClick={() => handleDelete(link.id)}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{editingId ? "Edit Link" : "Create Link"}</DialogTitle>
                        <DialogDescription>
                            {editingId ? "Update link details." : "Add a new navigation or social link."}
                        </DialogDescription>
                    </DialogHeader>
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                            <FormField
                                control={form.control}
                                name="title"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Title</FormLabel>
                                        <FormControl>
                                            <Input placeholder="GitHub" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="slug"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Slug</FormLabel>
                                        <FormControl>
                                            <Input placeholder="github" {...field} />
                                        </FormControl>
                                        <FormDescription>URL-friendly identifier</FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="url"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>URL</FormLabel>
                                        <FormControl>
                                            <Input placeholder="https://github.com/..." {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="icon"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Icon (optional)</FormLabel>
                                        <FormControl>
                                            <Input placeholder="🔗" {...field} />
                                        </FormControl>
                                        <FormDescription>Emoji or icon</FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <div className="grid grid-cols-3 gap-4">
                                <FormField
                                    control={form.control}
                                    name="status"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Status</FormLabel>
                                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="active">Active</SelectItem>
                                                    <SelectItem value="disabled">Disabled</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="visibility"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Visibility</FormLabel>
                                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="public">Public</SelectItem>
                                                    <SelectItem value="unlisted">Unlisted</SelectItem>
                                                    <SelectItem value="private">Private</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="position"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Position</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="number"
                                                    {...field}
                                                    onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <DialogFooter>
                                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                                    Cancel
                                </Button>
                                <Button type="submit">
                                    {editingId ? "Update" : "Create"}
                                </Button>
                            </DialogFooter>
                        </form>
                    </Form>
                </DialogContent>
            </Dialog>
        </div>
    )
}
