"use client"

import { type Editor } from "@tiptap/react"
import {
    Bold,
    Italic,
    Strikethrough,
    Code,
    Heading1,
    Heading2,
    Heading3,
    List,
    ListOrdered,
    Quote,
    Undo,
    Redo,
    Link as LinkIcon,
    Image as ImageIcon,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

interface ToolbarProps {
    editor: Editor | null
}

export function Toolbar({ editor }: ToolbarProps) {
    if (!editor) {
        return null
    }

    const setLink = () => {
        const previousUrl = editor.getAttributes('link').href
        const url = window.prompt('URL', previousUrl)

        // cancelled
        if (url === null) {
            return
        }

        // empty
        if (url === '') {
            editor.chain().focus().extendMarkRange('link').unsetLink().run()
            return
        }

        // update
        editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
    }

    const addImage = () => {
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = 'image/*'
        input.onchange = async (e) => {
            const file = (e.target as HTMLInputElement).files?.[0]
            if (file) {
                try {
                    const response = await import("@/lib/api").then(m => m.AssetsService.uploadAssetApiAssetsPost({ file }))
                    const url = `/assets/${response.id}/latest`
                    editor.chain().focus().setImage({ src: url }).run()
                } catch (error) {
                    console.error("Upload failed", error)
                    alert("Failed to upload image")
                }
            }
        }
        input.click()
    }

    // Helper for toolbar button styling
    const toolbarBtnClass = (active: boolean) => cn(
        "h-8 w-8 p-0",
        active && "bg-accent text-accent-foreground"
    )

    return (
        <div className="flex flex-wrap items-center gap-1 rounded-t-md border border-input bg-transparent p-1">
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("bold"))}
                onClick={() => editor.chain().focus().toggleBold().run()}
                title="Bold (Ctrl+B)"
            >
                <Bold className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("italic"))}
                onClick={() => editor.chain().focus().toggleItalic().run()}
                title="Italic (Ctrl+I)"
            >
                <Italic className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("strike"))}
                onClick={() => editor.chain().focus().toggleStrike().run()}
                title="Strikethrough"
            >
                <Strikethrough className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("code"))}
                onClick={() => editor.chain().focus().toggleCode().run()}
                title="Inline Code"
            >
                <Code className="h-4 w-4" />
            </Button>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("heading", { level: 1 }))}
                onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                title="Heading 1"
            >
                <Heading1 className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("heading", { level: 2 }))}
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                title="Heading 2"
            >
                <Heading2 className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("heading", { level: 3 }))}
                onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
                title="Heading 3"
            >
                <Heading3 className="h-4 w-4" />
            </Button>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("bulletList"))}
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                title="Bullet List"
            >
                <List className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("orderedList"))}
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                title="Numbered List"
            >
                <ListOrdered className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive("blockquote"))}
                onClick={() => editor.chain().focus().toggleBlockquote().run()}
                title="Quote"
            >
                <Quote className="h-4 w-4" />
            </Button>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <Button
                type="button"
                variant="ghost"
                size="sm"
                className={toolbarBtnClass(editor.isActive('link'))}
                onClick={setLink}
                title="Add Link"
            >
                <LinkIcon className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={addImage}
                title="Add Image"
            >
                <ImageIcon className="h-4 w-4" />
            </Button>

            <div className="flex-1" />

            <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => editor.chain().focus().undo().run()}
                disabled={!editor.can().undo()}
                title="Undo (Ctrl+Z)"
            >
                <Undo className="h-4 w-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => editor.chain().focus().redo().run()}
                disabled={!editor.can().redo()}
                title="Redo (Ctrl+Y)"
            >
                <Redo className="h-4 w-4" />
            </Button>
        </div>
    )
}
