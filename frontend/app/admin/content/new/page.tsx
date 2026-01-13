"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
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
import { Textarea } from "@/components/ui/textarea"
import { RichTextEditor } from "@/components/editor/RichTextEditor"
import { ContentService, ContentBlockModel, ContentCreateRequest } from "@/lib/api"

const formSchema = z.object({
    title: z.string().min(2, "Title must be at least 2 characters."),
    slug: z.string().min(2, "Slug must be at least 2 characters.")
        .regex(/^[a-z0-9-]+$/, "Slug must be lowercase alphanumeric with hyphens."),
    summary: z.string().optional(),
    body: z.any().optional(), // JSON object from TipTap
})

export default function NewContentPage() {
    const router = useRouter()
    const [saving, setSaving] = useState(false)

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            title: "",
            slug: "",
            summary: "",
            body: {},
        },
    })

    async function onSubmit(values: z.infer<typeof formSchema>) {
        try {
            setSaving(true)
            // Wrap TipTap JSON in blocks array
            const blocks = values.body ? [{
                block_type: ContentBlockModel.block_type.MARKDOWN,
                data_json: { tiptap: values.body },
                position: 0
            }] : []
            await ContentService.createContentApiContentPost({
                title: values.title,
                slug: values.slug,
                summary: values.summary,
                blocks: blocks,
                type: ContentCreateRequest.type.POST,
            })
            toast.success("Content created")
            router.push("/admin/content")
        } catch (error) {
            console.error(error)
            toast.error("Failed to create content")
        } finally {
            setSaving(false)
        }
    }

    // Auto-generate slug from title
    const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const title = e.target.value
        form.setValue("title", title)
        if (!form.getValues("slug")) {
            const slug = title.toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/(^-|-$)/g, '')
            form.setValue("slug", slug)
        }
    }

    return (
        <div className="space-y-6 max-w-4xl mx-auto py-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">New Content</h1>
                    <p className="text-muted-foreground">Create a new post or article.</p>
                </div>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                    <FormField
                        control={form.control}
                        name="title"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Title</FormLabel>
                                <FormControl>
                                    <Input placeholder="Post title" {...field} onChange={(e) => {
                                        field.onChange(e)
                                        handleTitleChange(e)
                                    }} />
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
                                <FormDescription>URL-friendly identifier.</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="summary"
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

                    <div className="flex justify-end gap-4">
                        <Button variant="outline" type="button" onClick={() => router.back()}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={saving}>
                            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Create Content
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    )
}
