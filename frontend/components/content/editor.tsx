"use client"

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { ContentBlockModel } from "@/lib/api"
import { useEffect, useState } from 'react'

interface EditorProps {
    initialBlocks?: ContentBlockModel[];
    onChange: (blocks: ContentBlockModel[]) => void;
}

export function Editor({ initialBlocks, onChange }: EditorProps) {
    // Simplified MVP: One main Tiptap instance for the "content"
    // We will serialize this back to a single "markdown" block for now to keep it simple,
    // or splitting by paragraphs if we want block-based.
    // Given the "Atomic Components" requirement, ideally we want separate blocks.
    // BUT Tiptap is a document editor.
    // Compromise: We use Tiptap for the main text body, and wrap it in a single "markdown" block.
    // Future: Split Tiptap JSON into blocks.

    // Actually, Tiptap gives HTML or JSON.
    // Let's store the whole Tiptap JSON dump into one "markdown" block (or "tiptap" block type if we added it, but "markdown" is close enough if we convert).
    // Let's stick to "markdown" and just extract text for now? No, that loses formatting.
    // Let's use `StarterKit` which supports basic markdown-like nodes.

    // REFACTOR PLAN:
    // We will treat the whole Tiptap document as ONE block of type "markdown" (containing HTML/JSON inside data_json)
    // OR we iterate the Tiptap JSON content array and map each top-level node to a ContentBlock.
    // Method 2 (Mapping) is better for "Atomic" blocks.

    // Let's try Method 2:
    // Tiptap Doc -> content: [ { type: 'paragraph', content: [...] }, { type: 'heading', ... } ]
    // We map each top-level Tiptap node to a `ContentBlockModel`.

    const editor = useEditor({
        extensions: [
            StarterKit,
        ],
        content: '', // Will init from effect
        onUpdate: ({ editor }) => {
            // Convert entire TipTap document to a single markdown block with HTML content
            const html = editor.getHTML();
            const block: ContentBlockModel = {
                block_type: ContentBlockModel.block_type.MARKDOWN,
                position: 0,
                data_json: { text: html }
            };
            onChange([block]);
        }
    })

    useEffect(() => {
        if (editor && initialBlocks && initialBlocks.length > 0) {
            // Find the first markdown block and set content
            const mdBlock = initialBlocks.find(b => b.block_type === 'markdown');
            if (mdBlock && mdBlock.data_json.text) {
                editor.commands.setContent(mdBlock.data_json.text);
            }
        }
    }, [editor, initialBlocks])

    if (!editor) {
        return null
    }

    return (
        <div className="border rounded-md p-4 min-h-[300px] prose dark:prose-invert max-w-none">
            <EditorContent editor={editor} />
        </div>
    )
}
