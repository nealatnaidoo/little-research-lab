"use client"

import { useEffect, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { RichTextEditor } from "@/components/editor/RichTextEditor"
import { ContentService } from "@/lib/api"
import { SchedulerService } from "@/lib/api/services/SchedulerService"
import { PublishingControls } from "@/components/content/publishing-controls"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

const formSchema = z.object({
    title: z.string().min(2, "Title must be at least 2 characters."),
    slug: z.string().min(2, "Slug must be at least 2 characters."),
    description: z.string().optional(),
    body: z.any().optional(),
})

export default function EditContentPage() {
    const router = useRouter()
    const params = useParams()
    const id = params.id as string

    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [deleting, setDeleting] = useState(false)
    const [currentStatus, setCurrentStatus] = useState("draft")
    const [publishAt, setPublishAt] = useState<string | null>(null)
    const [scheduledJobId, setScheduledJobId] = useState<string | null>(null)

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            title: "",
            slug: "",
            description: "",
            body: {},
        },
    })

    const fetchContent = useCallback(async () => {
        try {
            const item = await ContentService.get(id)
            form.reset({
                title: item.title,
                slug: item.slug,
                description: item.description || "",
                body: item.body || {},
            })
            setCurrentStatus(item.status)
            setPublishAt(item.publish_at || null)
            setScheduledJobId(item.scheduled_job_id || null)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load content")
            router.push("/admin/content")
        } finally {
            setLoading(false)
        }
    }, [id, form, router])

    useEffect(() => {
        fetchContent()
    }, [fetchContent])

    async function saveContent(showToast = true) {
        const values = form.getValues()
        try {
            setSaving(true)
            await ContentService.update(id, {
                title: values.title,
                slug: values.slug,
                description: values.description,
                body: values.body,
            })
            if (showToast) {
                toast.success("Content saved")
            }
        } catch (error) {
            console.error(error)
            toast.error("Failed to save content")
            throw error
        } finally {
            setSaving(false)
        }
    }

    async function onSubmit() {
        await saveContent(true)
    }

    async function onDelete() {
        try {
            setDeleting(true)
            await ContentService.delete(id)
            toast.success("Content deleted")
            router.push("/admin/content")
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete content")
        } finally {
            setDeleting(false)
        }
    }

    async function handlePublishNow() {
        try {
            // Save content first
            await saveContent(false)
            // Publish immediately
            await SchedulerService.publishNow(id)
            toast.success("Content published!")
            // Refresh content state
            await fetchContent()
        } catch (error) {
            console.error(error)
            toast.error("Failed to publish content")
            throw error
        }
    }

    async function handleSchedule(publishAtUtc: string) {
        try {
            // Save content first
            await saveContent(false)
            // Schedule job for future
            await SchedulerService.schedule(id, publishAtUtc)
            // Update content status to scheduled
            await ContentService.transition(id, { status: "scheduled", publish_at: publishAtUtc })
            toast.success("Content scheduled for publication")
            // Refresh content state
            await fetchContent()
        } catch (error) {
            console.error(error)
            toast.error("Failed to schedule content")
            throw error
        }
    }

    async function handleUnschedule() {
        try {
            // Cancel the scheduled job if it exists
            if (scheduledJobId) {
                await SchedulerService.unschedule(scheduledJobId)
            }
            // Transition content back to draft
            await ContentService.transition(id, { status: "draft" })
            toast.success("Publication cancelled")
            // Refresh content state
            await fetchContent()
        } catch (error) {
            console.error(error)
            toast.error("Failed to unschedule content")
            throw error
        }
    }

    async function handleUnpublish() {
        try {
            // Transition back to draft
            await ContentService.transition(id, { status: "draft" })
            toast.success("Content unpublished")
            // Refresh content state
            await fetchContent()
        } catch (error) {
            console.error(error)
            toast.error("Failed to unpublish content")
            throw error
        }
    }

    async function handleSaveDraft() {
        await saveContent(true)
    }

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="py-6">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Edit Content</h1>
                    <p className="text-muted-foreground">Manage your content.</p>
                </div>
                <AlertDialog>
                    <AlertDialogTrigger asChild>
                        <Button variant="destructive" size="icon" disabled={deleting}>
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Delete content?</AlertDialogTitle>
                            <AlertDialogDescription>
                                This action cannot be undone. This will permanently delete this content.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={onDelete} disabled={deleting}>
                                {deleting ? "Deleting..." : "Delete"}
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main content area */}
                <div className="lg:col-span-2">
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                            <div className="grid gap-4 md:grid-cols-2">
                                <FormField
                                    control={form.control}
                                    name="title"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Title</FormLabel>
                                            <FormControl>
                                                <Input placeholder="Post title" {...field} />
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
                                                <Input placeholder="post-slug" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control}
                                name="description"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Description</FormLabel>
                                        <FormControl>
                                            <Textarea placeholder="Short summary..." {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="body"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Body</FormLabel>
                                        <FormControl>
                                            <RichTextEditor
                                                onChange={field.onChange}
                                                content={field.value}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </form>
                    </Form>
                </div>

                {/* Sidebar */}
                <div className="space-y-4">
                    <PublishingControls
                        contentId={id}
                        currentStatus={currentStatus}
                        publishAt={publishAt}
                        scheduledJobId={scheduledJobId}
                        onPublishNow={handlePublishNow}
                        onSchedule={handleSchedule}
                        onUnschedule={handleUnschedule}
                        onUnpublish={handleUnpublish}
                        onSaveDraft={handleSaveDraft}
                        isSaving={saving}
                    />

                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            className="flex-1"
                            onClick={() => router.back()}
                        >
                            Cancel
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}
