"use client"

import Link from "next/link"
import { ArrowRight, Clock } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface RelatedArticle {
    id: string
    title: string
    slug: string
    summary?: string | null
    publish_at?: string | null
    created_at: string
}

interface RelatedArticlesProps {
    articles: RelatedArticle[]
    heading?: string
}

function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return ""
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
    })
}

export function RelatedArticles({
    articles,
    heading = "Related Articles",
}: RelatedArticlesProps) {
    if (articles.length === 0) {
        return null
    }

    return (
        <section className="mt-12 pt-8 border-t not-prose">
            <h2 className="text-lg font-semibold mb-6">{heading}</h2>
            <div className="grid gap-4 md:grid-cols-3">
                {articles.map((article) => (
                    <Link
                        key={article.id}
                        href={`/p/${article.slug}`}
                        className="group no-underline"
                    >
                        <Card className="h-full transition-colors hover:bg-muted/50">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base font-medium leading-snug group-hover:text-primary transition-colors">
                                    {article.title}
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {article.summary && (
                                    <p className="text-sm text-muted-foreground line-clamp-2">
                                        {article.summary}
                                    </p>
                                )}
                                <div className="flex items-center justify-between">
                                    <time className="text-xs text-muted-foreground">
                                        {formatDate(article.publish_at || article.created_at)}
                                    </time>
                                    <span className="text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                                        Read <ArrowRight className="h-3 w-3" />
                                    </span>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>
        </section>
    )
}

/**
 * Compact version for sidebar placement
 */
export function RelatedArticlesList({
    articles,
    heading = "Related",
}: RelatedArticlesProps) {
    if (articles.length === 0) {
        return null
    }

    return (
        <div className="space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                {heading}
            </h3>
            <ul className="space-y-2">
                {articles.map((article) => (
                    <li key={article.id}>
                        <Link
                            href={`/p/${article.slug}`}
                            className="text-sm text-foreground hover:text-primary transition-colors no-underline"
                        >
                            {article.title}
                        </Link>
                    </li>
                ))}
            </ul>
        </div>
    )
}
