import { ContentBlockModel } from "@/lib/api";

type BlockProps = {
    block: ContentBlockModel;
}

export function BlockRenderer({ block }: BlockProps) {
    if (!block.data_json) return null;

    // Parse data_json if it is a string (API client might type it as any/Record but it could be stringified JSON from backend?)
    // Our backend schema says `data_json` is `dict[str, Any]`.
    // In generated client `ContentBlock` -> `data_json: any`.

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
            // MVP: We are storing HTML in data_json.text from Tiptap.
            // We should dangerouslySetInnerHTML.
            return (
                <div
                    className="prose dark:prose-invert max-w-none my-4"
                    dangerouslySetInnerHTML={{ __html: data.text || "" }}
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
