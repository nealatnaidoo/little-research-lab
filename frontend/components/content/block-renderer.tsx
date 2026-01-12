import { generateHTML } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import { ContentBlockModel } from "@/lib/api";

type BlockProps = {
    block: ContentBlockModel;
}

// Extensions for generating HTML from TipTap JSON
const extensions = [
    StarterKit,
    Link.configure({ openOnClick: false }),
    Image,
];

export function BlockRenderer({ block }: BlockProps) {
    if (!block.data_json) return null;

    let data = block.data_json;
    if (typeof data === "string") {
        try {
            data = JSON.parse(data);
        } catch (e) {
            return <div className="text-red-500">Error parsing block data</div>;
        }
    }

    switch (block.block_type) {
        case "markdown":
            // Handle TipTap JSON format (new) or legacy text format
            let html = "";
            if (data.tiptap) {
                // New format: TipTap JSON document
                try {
                    html = generateHTML(data.tiptap, extensions);
                } catch (e) {
                    console.error("Error generating HTML from TipTap:", e);
                    html = "<p>Error rendering content</p>";
                }
            } else if (data.text) {
                // Legacy format: raw HTML/text
                html = data.text;
            }
            return (
                <div
                    className="prose dark:prose-invert max-w-none my-4"
                    dangerouslySetInnerHTML={{ __html: html }}
                />
            );
        case "image":
            return (
                <figure className="my-6">
                    <img
                        src={data.url}
                        alt={data.alt || "Post image"}
                        className="rounded-lg border w-full h-auto max-h-[600px] object-cover"
                    />
                    {data.caption && (
                        <figcaption className="text-center text-sm text-muted-foreground mt-2">
                            {data.caption}
                        </figcaption>
                    )}
                </figure>
            )
        case "embed":
            return (
                <div className="my-6 border rounded p-4 bg-muted text-center text-sm">
                    Embed: {data.url}
                </div>
            );
        default:
            return <div className="text-xs text-muted-foreground">Unknown block type: {block.block_type}</div>;
    }
}
