"use client"

import { useEditor, EditorContent } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Link from "@tiptap/extension-link"
import Image from "@tiptap/extension-image"
import { Toolbar } from "./Toolbar"

interface RichTextEditorProps {
    content?: string | object // HTML or JSON
    onChange: (content: object) => void // We emit JSON for the backend
    editable?: boolean
}

export function RichTextEditor({ content = "", onChange, editable = true }: RichTextEditorProps) {
    const editor = useEditor({
        extensions: [
            StarterKit,
            Link.configure({
                openOnClick: false,
            }),
            Image,
        ],
        content: content,
        editable: editable,
        onUpdate: ({ editor }) => {
            onChange(editor.getJSON())
        },
        editorProps: {
            attributes: {
                class: "min-h-[200px] w-full rounded-b-md border border-t-0 border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 prose prose-sm dark:prose-invert max-w-none",
            },
        },
    })

    return (
        <div className="flex flex-col">
            <Toolbar editor={editor} />
            <EditorContent editor={editor} />
        </div>
    )
}
