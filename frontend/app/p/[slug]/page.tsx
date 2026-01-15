import { notFound } from "next/navigation";
import Link from "next/link";
import { OpenAPI, PublicService, ContentItemResponse } from "@/lib/api";
import { BlockRenderer } from "@/components/content/block-renderer";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { ArticleReader, EngagementTracker, TextToSpeechControls, ShareButtons, NewsletterSignupInline, RelatedArticles } from "@/components/reader";
import { PaywallOverlay, type ContentTier } from "@/components/content/paywall-overlay";
import { ArrowLeft, Clock, Lock } from "lucide-react";
import { extractTextFromBlocks } from "@/lib/extractText";
import { checkContentAccess, filterContentBlocks } from "@/lib/monetization";

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

    // Get content tier (default to "free" for backwards compatibility)
    const contentTier = (post.tier as ContentTier) || "free";

    // For MVP, all users have "free" entitlement (via PaymentStubAdapter)
    // In production, this would come from session/auth check
    const userEntitlement = "free" as const;

    // Server-side tier access enforcement (I10, R8)
    const blocks = post.blocks || [];
    const { visibleBlocks, totalBlocks, hiddenBlocks, isPreview } = filterContentBlocks(
        blocks,
        contentTier,
        userEntitlement
    );

    // Extract plain text for TTS and word count (only from visible blocks)
    const articleText = extractTextFromBlocks(visibleBlocks);
    const wordCount = articleText.split(/\s+/).filter(Boolean).length;
    const readingTime = Math.max(1, Math.ceil(wordCount / 200));

    // Check if content is gated
    const isGated = contentTier !== "free" && isPreview;

    // Fetch related articles (only for non-gated content or full access)
    let relatedArticles: ContentItemResponse[] = [];
    if (!isGated) {
        try {
            relatedArticles = await PublicService.getRelatedArticlesApiPublicContentContentIdRelatedGet(
                post.id,
                3
            );
        } catch (error) {
            // Graceful degradation - don't break page if related articles fail
            console.error("Failed to fetch related articles", error);
        }
    }

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
                    <div className="flex items-center justify-center gap-4 text-muted-foreground flex-wrap">
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
                        {/* Show tier badge for gated content */}
                        {contentTier !== "free" && (
                            <>
                                <span className="text-muted-foreground/50">|</span>
                                <span className="inline-flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
                                    <Lock className="h-4 w-4" />
                                    {contentTier === "premium" ? "Premium" : "Subscriber"}
                                </span>
                            </>
                        )}
                        <span className="text-muted-foreground/50">|</span>
                        <TextToSpeechControls text={articleText} />
                        <span className="text-muted-foreground/50">|</span>
                        <ShareButtons
                            contentId={post.id}
                            slug={slug}
                            title={post.title}
                        />
                    </div>
                </header>

                <article>
                    {/* Server-side enforcement: only visible blocks are rendered (I10, R8) */}
                    {visibleBlocks.map((block) => (
                        <BlockRenderer key={block.id || block.position} block={block} />
                    ))}
                </article>

                {/* Paywall overlay for gated content */}
                {isGated && (
                    <PaywallOverlay
                        requiredTier={contentTier}
                        previewBlocksShown={visibleBlocks.length}
                        totalBlocks={totalBlocks}
                    />
                )}

                {/* Newsletter signup - only show for non-gated or full-access */}
                {!isGated && (
                    <NewsletterSignupInline
                        heading="Enjoyed this article?"
                        description="Subscribe to get notified when new articles are published."
                    />
                )}

                {/* Related articles - only show for non-gated content */}
                {!isGated && relatedArticles.length > 0 && (
                    <RelatedArticles articles={relatedArticles} />
                )}

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
