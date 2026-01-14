import { notFound } from "next/navigation";
import Link from "next/link";
import { OpenAPI, PublicService, ContentItemResponse } from "@/lib/api";
import { BlockRenderer } from "@/components/content/block-renderer";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { ArticleReader, EngagementTracker } from "@/components/reader";
import { ArrowLeft, Clock } from "lucide-react";

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

    // Estimate reading time (rough: 200 words per minute)
    const wordCount = post.blocks?.reduce((acc, block) => {
        const text = JSON.stringify(block.data_json || "");
        return acc + text.split(/\s+/).length;
    }, 0) || 0;
    const readingTime = Math.max(1, Math.ceil(wordCount / 200));

    return (
        <PublicLayout>
            {/* Track engagement (time on page + scroll depth) */}
            <EngagementTracker contentId={post.id} path={`/p/${slug}`} />

            <ArticleReader className="container mx-auto px-4 py-12">
                <Link
                    href="/"
                    className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors no-underline"
                >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Home
                </Link>

                <header className="mb-10 text-center not-prose">
                    <h1 className="text-4xl md:text-5xl font-bold mb-4 text-foreground tracking-tight">
                        {post.title}
                    </h1>
                    <div className="flex items-center justify-center gap-4 text-muted-foreground">
                        <time dateTime={post.publish_at || post.created_at}>
                            {new Date(post.publish_at || post.created_at).toLocaleDateString("en-GB", {
                                day: "numeric",
                                month: "long",
                                year: "numeric",
                            })}
                        </time>
                        <span className="text-muted-foreground/50">|</span>
                        <span className="inline-flex items-center gap-1.5">
                            <Clock className="h-4 w-4" />
                            {readingTime} min read
                        </span>
                    </div>
                </header>

                <article>
                    {post.blocks?.map((block) => (
                        <BlockRenderer key={block.id || block.position} block={block} />
                    ))}
                </article>

                {/* Article footer */}
                <footer className="mt-12 pt-8 border-t not-prose">
                    <div className="text-center text-muted-foreground text-sm">
                        Thanks for reading
                    </div>
                </footer>
            </ArticleReader>
        </PublicLayout>
    );
}
