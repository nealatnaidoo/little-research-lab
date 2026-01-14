"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, Loader2, FileText } from "lucide-react"
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
import { AdminResourcesService, AssetsService, type AssetResponse } from "@/lib/api"

export default function NewResourcePage() {
    const router = useRouter()
    const [loading, setLoading] = useState(false)
    const [assets, setAssets] = useState<AssetResponse[]>([])
    const [loadingAssets, setLoadingAssets] = useState(true)

    // Form state
    const [title, setTitle] = useState("")
    const [slug, setSlug] = useState("")
    const [summary, setSummary] = useState("")
    const [pdfAssetId, setPdfAssetId] = useState<string>("")
    const [pinnedPolicy, setPinnedPolicy] = useState<"latest" | "pinned">("latest")
    const [displayTitle, setDisplayTitle] = useState("")
    const [downloadFilename, setDownloadFilename] = useState("")

    useEffect(() => {
        fetchAssets()
    }, [])

    const fetchAssets = async () => {
        try {
            const data = await AssetsService.listAssetsApiAssetsGet()
            // Filter to only PDF assets
            const pdfAssets = data.filter(a => a.mime_type === "application/pdf")
            setAssets(pdfAssets)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load assets")
        } finally {
            setLoadingAssets(false)
        }
    }

    // Auto-generate slug from title
    const handleTitleChange = (value: string) => {
        setTitle(value)
        // Only auto-generate if slug hasn't been manually edited
        if (!slug || slug === generateSlug(title)) {
            setSlug(generateSlug(value))
        }
    }

    const generateSlug = (text: string) => {
        return text
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-|-$/g, "")
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!title.trim()) {
            toast.error("Title is required")
            return
        }
        if (!slug.trim()) {
            toast.error("Slug is required")
            return
        }

        setLoading(true)
        try {
            const resource = await AdminResourcesService.createResource({
                title: title.trim(),
                slug: slug.trim(),
                summary: summary.trim() || undefined,
                pdf_asset_id: pdfAssetId || undefined,
                pinned_policy: pinnedPolicy,
                display_title: displayTitle.trim() || undefined,
                download_filename: downloadFilename.trim() || undefined,
            })

            toast.success("Resource created!")
            router.push(`/admin/resources/${resource.id}`)
        } catch (error: unknown) {
            console.error(error)
            const message = error instanceof Error ? error.message : "Failed to create resource"
            toast.error(message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" asChild>
                    <Link href="/admin/resources">
                        <ArrowLeft className="h-4 w-4" />
                    </Link>
                </Button>
                <div className="flex items-center gap-3">
                    <FileText className="h-6 w-6 text-muted-foreground" />
                    <h1 className="text-2xl font-bold">New PDF Resource</h1>
                </div>
            </div>

            <form onSubmit={handleSubmit}>
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
                                        onChange={(e) => handleTitleChange(e.target.value)}
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
                                    {loadingAssets ? (
                                        <div className="flex items-center gap-2 text-muted-foreground">
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                            Loading assets...
                                        </div>
                                    ) : assets.length === 0 ? (
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
                                    <p className="text-xs text-muted-foreground">
                                        Choose whether to always serve the latest PDF version or pin to a specific version.
                                    </p>
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
                                    <p className="text-xs text-muted-foreground">
                                        If set, this will be shown instead of the main title on the public page.
                                    </p>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="download-filename">Download Filename (optional)</Label>
                                    <Input
                                        id="download-filename"
                                        value={downloadFilename}
                                        onChange={(e) => setDownloadFilename(e.target.value)}
                                        placeholder="custom-filename.pdf"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Custom filename when users download the PDF.
                                    </p>
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
                                <Button type="submit" className="w-full" disabled={loading}>
                                    {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Create Draft
                                </Button>
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="w-full"
                                    onClick={() => router.push("/admin/resources")}
                                >
                                    Cancel
                                </Button>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Help</CardTitle>
                            </CardHeader>
                            <CardContent className="text-sm text-muted-foreground space-y-2">
                                <p>
                                    PDF Resources allow you to publish downloadable documents with
                                    proper meta tags for SEO and social sharing.
                                </p>
                                <p>
                                    After creating the draft, you can preview it and publish when ready.
                                </p>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </form>
        </div>
    )
}
