"use client"

import { useState, useEffect, use } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, Loader2, FileText, Trash2, ExternalLink, Send } from "lucide-react"
import Link from "next/link"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
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
import { Badge } from "@/components/ui/badge"
import {
    AdminResourcesService,
    AdminScheduleService,
    AssetsService,
    type AssetResponse,
    type ResourcePDFResponse,
} from "@/lib/api"

interface PageProps {
    params: Promise<{ id: string }>
}

export default function EditResourcePage({ params }: PageProps) {
    const { id } = use(params)
    const router = useRouter()
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [publishing, setPublishing] = useState(false)
    const [assets, setAssets] = useState<AssetResponse[]>([])
    const [resource, setResource] = useState<ResourcePDFResponse | null>(null)

    // Form state
    const [title, setTitle] = useState("")
    const [slug, setSlug] = useState("")
    const [summary, setSummary] = useState("")
    const [pdfAssetId, setPdfAssetId] = useState<string>("")
    const [pinnedPolicy, setPinnedPolicy] = useState<"latest" | "pinned">("latest")
    const [displayTitle, setDisplayTitle] = useState("")
    const [downloadFilename, setDownloadFilename] = useState("")

    useEffect(() => {
        fetchResource()
        fetchAssets()
    }, [id])

    const fetchResource = async () => {
        try {
            const data = await AdminResourcesService.getResource(id)
            setResource(data)
            // Populate form
            setTitle(data.title)
            setSlug(data.slug)
            setSummary(data.summary || "")
            setPdfAssetId(data.pdf_asset_id || "")
            setPinnedPolicy(data.pinned_policy)
            setDisplayTitle(data.display_title || "")
            setDownloadFilename(data.download_filename || "")
        } catch (error) {
            console.error(error)
            toast.error("Failed to load resource")
            router.push("/admin/resources")
        } finally {
            setLoading(false)
        }
    }

    const fetchAssets = async () => {
        try {
            const data = await AssetsService.listAssetsApiAssetsGet()
            const pdfAssets = data.filter(a => a.mime_type === "application/pdf")
            setAssets(pdfAssets)
        } catch (error) {
            console.error(error)
        }
    }

    const handleSave = async () => {
        if (!title.trim()) {
            toast.error("Title is required")
            return
        }
        if (!slug.trim()) {
            toast.error("Slug is required")
            return
        }

        setSaving(true)
        try {
            const updated = await AdminResourcesService.updateResource(id, {
                title: title.trim(),
                slug: slug.trim(),
                summary: summary.trim() || undefined,
                pdf_asset_id: pdfAssetId || undefined,
                pinned_policy: pinnedPolicy,
                display_title: displayTitle.trim() || undefined,
                download_filename: downloadFilename.trim() || undefined,
            })
            setResource(updated)
            toast.success("Changes saved!")
        } catch (error: unknown) {
            console.error(error)
            const message = error instanceof Error ? error.message : "Failed to save changes"
            toast.error(message)
        } finally {
            setSaving(false)
        }
    }

    const handlePublish = async () => {
        if (!pdfAssetId) {
            toast.error("Please select a PDF file before publishing")
            return
        }

        setPublishing(true)
        try {
            await AdminScheduleService.publishNowApiAdminSchedulePublishNowPost({
                content_id: id,
            })
            toast.success("Resource published!")
            fetchResource()
        } catch (error: unknown) {
            console.error(error)
            const message = error instanceof Error ? error.message : "Failed to publish"
            toast.error(message)
        } finally {
            setPublishing(false)
        }
    }

    const handleDelete = async () => {
        try {
            await AdminResourcesService.deleteResource(id)
            toast.success("Resource deleted")
            router.push("/admin/resources")
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete resource")
        }
    }

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "published":
                return <Badge variant="success">Published</Badge>
            case "scheduled":
                return (
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                        Scheduled
                    </Badge>
                )
            case "draft":
            default:
                return <Badge variant="secondary">Draft</Badge>
        }
    }

    if (loading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (!resource) {
        return null
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild>
                        <Link href="/admin/resources">
                            <ArrowLeft className="h-4 w-4" />
                        </Link>
                    </Button>
                    <div className="flex items-center gap-3">
                        <FileText className="h-6 w-6 text-muted-foreground" />
                        <h1 className="text-2xl font-bold">Edit Resource</h1>
                        {getStatusBadge(resource.status)}
                    </div>
                </div>
                {resource.status === "published" && (
                    <Button variant="outline" asChild>
                        <Link href={`/r/${resource.slug}`} target="_blank">
                            <ExternalLink className="mr-2 h-4 w-4" />
                            View Public
                        </Link>
                    </Button>
                )}
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                {/* Main Form */}
                <div className="lg:col-span-2 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Basic Information</CardTitle>
                            <CardDescription>
                                Set the title, slug, and description for your PDF resource.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="title">Title *</Label>
                                <Input
                                    id="title"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="My Research Paper"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="slug">Slug *</Label>
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">/r/</span>
                                    <Input
                                        id="slug"
                                        value={slug}
                                        onChange={(e) => setSlug(e.target.value)}
                                        placeholder="my-research-paper"
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    URL-friendly identifier. Only lowercase letters, numbers, and hyphens.
                                </p>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="summary">Summary</Label>
                                <Textarea
                                    id="summary"
                                    value={summary}
                                    onChange={(e) => setSummary(e.target.value)}
                                    placeholder="A brief description of this resource..."
                                    rows={3}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>PDF Asset</CardTitle>
                            <CardDescription>
                                Select the PDF file to link to this resource.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="pdf-asset">PDF File</Label>
                                {assets.length === 0 ? (
                                    <div className="text-sm text-muted-foreground p-4 border border-dashed rounded-md">
                                        No PDF assets found.{" "}
                                        <Link href="/admin/assets" className="text-primary hover:underline">
                                            Upload a PDF
                                        </Link>{" "}
                                        first.
                                    </div>
                                ) : (
                                    <Select value={pdfAssetId} onValueChange={setPdfAssetId}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select a PDF file" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="">No PDF selected</SelectItem>
                                            {assets.map((asset) => (
                                                <SelectItem key={asset.id} value={asset.id}>
                                                    {asset.filename_original}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="pinned-policy">Version Policy</Label>
                                <Select
                                    value={pinnedPolicy}
                                    onValueChange={(v) => setPinnedPolicy(v as "latest" | "pinned")}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="latest">
                                            Always Latest - Automatically use newest version
                                        </SelectItem>
                                        <SelectItem value="pinned" disabled>
                                            Pinned - Use a specific version (coming soon)
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Display Options</CardTitle>
                            <CardDescription>
                                Optional settings for how the resource appears.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="display-title">Display Title (optional)</Label>
                                <Input
                                    id="display-title"
                                    value={displayTitle}
                                    onChange={(e) => setDisplayTitle(e.target.value)}
                                    placeholder="Override title for display"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="download-filename">Download Filename (optional)</Label>
                                <Input
                                    id="download-filename"
                                    value={downloadFilename}
                                    onChange={(e) => setDownloadFilename(e.target.value)}
                                    placeholder="custom-filename.pdf"
                                />
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Actions</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Button onClick={handleSave} className="w-full" disabled={saving}>
                                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Save Changes
                            </Button>

                            {resource.status === "draft" && (
                                <Button
                                    onClick={handlePublish}
                                    variant="default"
                                    className="w-full bg-green-600 hover:bg-green-700"
                                    disabled={publishing || !pdfAssetId}
                                >
                                    {publishing ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <Send className="mr-2 h-4 w-4" />
                                    )}
                                    Publish Now
                                </Button>
                            )}

                            <AlertDialog>
                                <AlertDialogTrigger asChild>
                                    <Button variant="destructive" className="w-full">
                                        <Trash2 className="mr-2 h-4 w-4" />
                                        Delete Resource
                                    </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                    <AlertDialogHeader>
                                        <AlertDialogTitle>Delete this resource?</AlertDialogTitle>
                                        <AlertDialogDescription>
                                            This action cannot be undone. The resource will be permanently deleted.
                                        </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                                        <AlertDialogAction onClick={handleDelete}>
                                            Delete
                                        </AlertDialogAction>
                                    </AlertDialogFooter>
                                </AlertDialogContent>
                            </AlertDialog>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Info</CardTitle>
                        </CardHeader>
                        <CardContent className="text-sm text-muted-foreground space-y-2">
                            <div className="flex justify-between">
                                <span>Status</span>
                                <span className="text-foreground">{resource.status}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Created</span>
                                <span className="text-foreground">
                                    {new Date(resource.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span>Updated</span>
                                <span className="text-foreground">
                                    {new Date(resource.updated_at).toLocaleDateString()}
                                </span>
                            </div>
                            {resource.published_at && (
                                <div className="flex justify-between">
                                    <span>Published</span>
                                    <span className="text-foreground">
                                        {new Date(resource.published_at).toLocaleDateString()}
                                    </span>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
