"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation" // NOTE: params are async in some versions, but this is client component so we use params prop or hook? 
// In Next.js app router, page.tsx receives params.
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2 } from "lucide-react"
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { ContentService, ContentBlockModel } from "@/lib/api"
import { Editor } from "@/components/content/editor"

const formSchema = z.object({
    title: z.string().min(1, "Title is required"),
    slug: z.string().min(1, "Slug is required"),
    status: z.enum(["draft", "published", "archived", "scheduled"]),
})
// Fix for params:
// Page props: { params: { id: string } }
// In async component: params is promise.
// In client component: we should probably wrap or use React.use() if we were using it inside.
// Actually standard pattern: passed as prop.

export default function EditContentPage({ params }: any) {
    // Unwrapping params if it's a promise (Next.js 15)
    // Efficient Hack: just assume we can get id from params async or sync.
    // Ideally we make this component async? No, client component cannot be async essentially in the same way.
    // Correct way for Client Component: `useParams()` hook from `next/navigation`
    // Let's use `useParams()` to be safe!
    return <EditContentForm />
}

import { useParams } from "next/navigation"

function EditContentForm() {
    const router = useRouter()
    const params = useParams()
    const id = params.id as string

    const [isLoading, setIsLoading] = useState(false)
    const [blocks, setBlocks] = useState<ContentBlockModel[]>([])
    const [isFetching, setIsFetching] = useState(true)

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            title: "",
            slug: "",
            status: "draft"
        },
    })

    useEffect(() => {
        if (id) {
            loadItem(id)
        }
    }, [id])

    async function loadItem(itemId: string) {
        try {
            const item = await ContentService.getContentApiContentItemIdGet(itemId)
            form.reset({
                title: item.title,
                slug: item.slug,
                status: item.status as any // Cast to ensure compatibility with form schema
            })
            setBlocks(item.blocks || [])
        } catch (e) {
            toast.error("Failed to load item")
            router.push("/admin/content")
        } finally {
            setIsFetching(false)
        }
    }

    async function onSubmit(values: z.infer<typeof formSchema>) {
        setIsLoading(true)
        try {
            await ContentService.updateContentApiContentItemIdPut(id, {
                title: values.title,
                slug: values.slug,
                status: values.status as any,
                blocks: blocks
            });
            toast.success("Content saved")
        } catch (e) {
            console.error(e)
            toast.error("Failed to save content")
        } finally {
            setIsLoading(false)
        }
    }

    if (isFetching) return <div>Loading...</div>

    return (
        <div className="space-y-6 max-w-3xl">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Edit Content</h1>
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
                                    <Input {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="grid grid-cols-2 gap-4">
                        <FormField
                            control={form.control}
                            name="slug"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Slug</FormLabel>
                                    <FormControl>
                                        <Input {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="status"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Status</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select status" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="draft">Draft</SelectItem>
                                            <SelectItem value="published">Published</SelectItem>
                                            <SelectItem value="archived">Archived</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <div className="space-y-2">
                        <FormLabel>Content</FormLabel>
                        {/* We pass initialBlocks to editor */}
                        <Editor initialBlocks={blocks} onChange={setBlocks} />
                    </div>

                    <div className="flex justify-end gap-2">
                        <Button variant="outline" type="button" onClick={() => router.back()}>Back</Button>
                        <Button type="submit" disabled={isLoading}>
                            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Save
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    )
}
