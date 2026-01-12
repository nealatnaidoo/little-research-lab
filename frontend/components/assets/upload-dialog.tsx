"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Upload, X, File as FileIcon, Loader2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { AssetsService } from "@/lib/api"

interface UploadDialogProps {
    onUploadConfig?: () => void; // Callback to refresh list
    children?: React.ReactNode;
}

export function UploadDialog({ onUploadConfig, children }: UploadDialogProps) {
    const [open, setOpen] = useState(false)
    const [file, setFile] = useState<File | null>(null)
    const [isLoading, setIsLoading] = useState(false)

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
        }
    }

    const handleUpload = async () => {
        if (!file) return;

        setIsLoading(true);
        try {
            // AssetsService.uploadAssetApiAssetsPost expects 'formData': Body_upload_asset_api_assets_post
            // which contains 'file': Blob | File
            await AssetsService.uploadAssetApiAssetsPost({
                file: file
            });
            toast.success("File uploaded successfully");
            setOpen(false);
            setFile(null);
            if (onUploadConfig) onUploadConfig();
        } catch (e) {
            console.error(e);
            toast.error("Upload failed");
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {children || (
                    <Button>
                        <Upload className="mr-2 h-4 w-4" />
                        Upload Asset
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Upload Asset</DialogTitle>
                    <DialogDescription>
                        Select a file to upload to the library.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="file" className="text-right">
                            File
                        </Label>
                        <Input
                            id="file"
                            type="file"
                            className="col-span-3"
                            data-testid="assets-upload-input"
                            onChange={handleFileChange}
                        />
                    </div>
                    {file && (
                        <div className="flex items-center gap-2 p-2 border rounded bg-muted/50 text-sm">
                            <FileIcon className="h-4 w-4" />
                            <span className="truncate flex-1">{file.name}</span>
                            <Button variant="ghost" size="sm" onClick={() => setFile(null)}>
                                <X className="h-3 w-3" />
                            </Button>
                        </div>
                    )}
                </div>
                <DialogFooter>
                    <Button onClick={handleUpload} disabled={!file || isLoading} data-testid="assets-upload-submit">
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Upload
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
