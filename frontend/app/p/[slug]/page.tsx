import { notFound } from "next/navigation";
import Link from "next/link";
import { OpenAPI, PublicService, ContentItemResponse } from "@/lib/api";
import { BlockRenderer } from "@/components/content/block-renderer";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { ArrowLeft } from "lucide-react";

// Force dynamic rendering - fetch fresh post data on each request
export const dynamic = 'force-dynamic';

// Ensure Server Config
OpenAPI.BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// In Next.js 16, params is a Promise and must be awaited
interface PageProps {
    params: Promise<{ slug: string }>;
}

export default async function PostPage({ params }: PageProps) {
    const { slug } = await params;

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
        <PublicLayout>
            <div className="container mx-auto px-4 py-12 max-w-3xl">
            <Link
                href="/"
                className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors"
            >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
            </Link>
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
        </PublicLayout>
    );
}
