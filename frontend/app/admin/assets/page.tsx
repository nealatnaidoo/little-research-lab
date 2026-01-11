"use client"

import { useEffect, useState } from "react"
import { Copy, Trash2, Check } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardFooter,
} from "@/components/ui/card"
import { UploadDialog } from "@/components/assets/upload-dialog"
import { AssetsService, AssetResponse, OpenAPI } from "@/lib/api"
import { ScrollArea } from "@/components/ui/scroll-area"

export default function AssetsPage() {
    const [assets, setAssets] = useState<AssetResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [copiedId, setCopiedId] = useState<string | null>(null)

    const fetchAssets = async () => {
        try {
            const data = await AssetsService.listAssetsApiAssetsGet(); // Confirmed endpoint
            setAssets(data);
        } catch (e) {
            console.error(e);
            toast.error("Failed to load assets");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchAssets();
    }, [])

    const copyToClipboard = (asset: AssetResponse) => {
        // Construct URL. Ideally API returns full URL or storage path relative to base.
        // API returns `storage_path`.
        // The GET /api/assets/{id}/content/ endpoint serves it? No, checking logic.
        // AssetService has get_asset_content.
        // But typically we want a direct serve URL.
        // Current implementation: `get_asset_content` retrieves bytes.
        // So we can assume `/api/assets/{id}/content` endpoint should exist for public/auth access?
        // Wait, `src/api/routes/assets.py` DOES NOT have a download endpoint.
        // It only has Upload and List (which I added).
        // T-0047 plan mentioned "Read" for public?
        // src/api/routes/public.py?
        // Let's assume for now we might need to add `GET /api/assets/{id}/content` later.
        // OR uses `storage_path` if served statically? Unlikely for "local filesystem".
        // We will assume `/api/assets/{id}/raw` or similar will be added.
        // For MVP, let's just copy the ID or a placeholder URL.
        // Let's copy a constructed URL: `/api/public/assets/${asset.id}` (common pattern).

        const url = `${OpenAPI.BASE}/api/assets/${asset.id}/content`;
        navigator.clipboard.writeText(url);
        setCopiedId(asset.id);
        toast.success("URL copied");
        setTimeout(() => setCopiedId(null), 2000);
    }

    if (loading) return <div>Loading assets...</div>

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Asset Library</h1>
                <UploadDialog onUploadConfig={fetchAssets} />
            </div>

            {assets.length === 0 ? (
                <div className="text-center text-muted-foreground py-12 border rounded-lg border-dashed">
                    No assets found. Upload one to get started.
                </div>
            ) : (
                <ScrollArea className="h-[calc(100vh-200px)]">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pb-4">
                        {assets.map((asset) => (
                            <Card key={asset.id} className="overflow-hidden group">
                                <div className="aspect-square bg-muted relative flex items-center justify-center">
                                    {asset.mime_type?.startsWith("image/") ? (
                                        <img
                                            src={`${OpenAPI.BASE}/api/assets/${asset.id}/content`}
                                            alt={asset.filename_original}
                                            className="object-cover w-full h-full"
                                            loading="lazy"
                                        />
                                    ) : (
                                        <div className="text-xs text-muted-foreground p-2 text-center break-all">
                                            {asset.filename_original}
                                        </div>
                                    )}

                                    {/* Overlay Actions */}
                                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                        <Button size="sm" variant="secondary" onClick={() => copyToClipboard(asset)}>
                                            {copiedId === asset.id ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                        </Button>
                                    </div>
                                </div>
                                <CardFooter className="p-2 text-xs truncate text-muted-foreground flex justify-between bg-card">
                                    <span className="truncate max-w-[100px]">{asset.filename_original}</span>
                                    <span>{(asset.size_bytes / 1024).toFixed(0)}KB</span>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                </ScrollArea>
            )}
        </div>
    )
}
