import { notFound } from "next/navigation";
import { OpenAPI, PublicService, ContentItemResponse } from "@/lib/api";
import { BlockRenderer } from "@/components/content/block-renderer";

// Ensure Server Config
OpenAPI.BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PageProps {
    params: {
        slug: string;
    }
}

// In Next.js 15+ params is async? Checking package.json -> next: 16.1.1
// Yes, params should be awaited or treated as Promise in recent versions.
interface PageProps {
    params: { slug: string };
}

export default async function PostPage({ params }: PageProps) {
    const { slug } = params;

    let post: ContentItemResponse | null = null;
    try {
        post = await PublicService.getPublicContentApiPublicContentSlugGet(slug);
    } catch (error) {
        console.error("Error fetching post", error);
    }

    if (!post) {
        notFound();
    }

    return (
        <div className="container mx-auto px-4 py-12 max-w-3xl">
            <header className="mb-8 text-center">
                <h1 className="text-4xl font-bold mb-4 text-foreground">{post.title}</h1>
                <div className="text-muted-foreground">
                    {new Date(post.publish_at || post.created_at).toLocaleDateString()}
                </div>
            </header>

            <article>
                {post.blocks?.map((block) => (
                    <BlockRenderer key={block.id || block.position} block={block} />
                ))}
            </article>
        </div>
    );
}
