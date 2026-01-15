"use client"

import { Lock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

export type ContentTier = "free" | "premium" | "subscriber_only"

interface PaywallOverlayProps {
    /**
     * The tier required to access this content
     */
    requiredTier: ContentTier
    /**
     * Number of preview blocks shown (for messaging)
     */
    previewBlocksShown?: number
    /**
     * Total blocks in the content
     */
    totalBlocks?: number
    /**
     * Callback when user clicks upgrade/subscribe
     */
    onUpgradeClick?: () => void
    /**
     * Custom CTA text (default depends on tier)
     */
    ctaText?: string
}

const TIER_LABELS: Record<ContentTier, string> = {
    free: "Free",
    premium: "Premium",
    subscriber_only: "Subscriber",
}

const TIER_DESCRIPTIONS: Record<ContentTier, string> = {
    free: "This content is available to everyone.",
    premium: "This content is exclusive to premium members.",
    subscriber_only: "This content is exclusive to active subscribers.",
}

export function PaywallOverlay({
    requiredTier,
    previewBlocksShown = 0,
    totalBlocks = 0,
    onUpgradeClick,
    ctaText,
}: PaywallOverlayProps) {
    const defaultCtaText =
        requiredTier === "subscriber_only" ? "Subscribe Now" : "Upgrade to Premium"

    const remainingBlocks = totalBlocks - previewBlocksShown

    return (
        <div className="relative">
            {/* Gradient fade overlay */}
            <div className="absolute inset-x-0 -top-24 h-24 bg-gradient-to-t from-background to-transparent pointer-events-none" />

            {/* Paywall card */}
            <Card className="border-2 border-dashed border-muted-foreground/25 bg-muted/50">
                <CardHeader className="text-center pb-2">
                    <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                        <Lock className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-lg">
                        {TIER_LABELS[requiredTier]} Content
                    </CardTitle>
                </CardHeader>
                <CardContent className="text-center pb-4">
                    <p className="text-muted-foreground text-sm mb-2">
                        {TIER_DESCRIPTIONS[requiredTier]}
                    </p>
                    {remainingBlocks > 0 && (
                        <p className="text-sm text-muted-foreground">
                            {previewBlocksShown > 0 ? (
                                <>
                                    You&apos;ve seen a preview.{" "}
                                    <span className="font-medium text-foreground">
                                        {remainingBlocks} more{" "}
                                        {remainingBlocks === 1 ? "section" : "sections"}
                                    </span>{" "}
                                    available with {TIER_LABELS[requiredTier].toLowerCase()}{" "}
                                    access.
                                </>
                            ) : (
                                <>
                                    This article has{" "}
                                    <span className="font-medium text-foreground">
                                        {totalBlocks} {totalBlocks === 1 ? "section" : "sections"}
                                    </span>{" "}
                                    available with {TIER_LABELS[requiredTier].toLowerCase()}{" "}
                                    access.
                                </>
                            )}
                        </p>
                    )}
                </CardContent>
                <CardFooter className="justify-center pt-0">
                    <Button onClick={onUpgradeClick} size="lg">
                        {ctaText || defaultCtaText}
                    </Button>
                </CardFooter>
            </Card>
        </div>
    )
}

/**
 * A simplified inline paywall message for less prominent placement
 */
export function PaywallInline({
    requiredTier,
    onUpgradeClick,
    ctaText,
}: {
    requiredTier: ContentTier
    onUpgradeClick?: () => void
    ctaText?: string
}) {
    const defaultCtaText =
        requiredTier === "subscriber_only" ? "Subscribe" : "Upgrade"

    return (
        <div className="flex items-center gap-3 rounded-lg border border-dashed border-muted-foreground/25 bg-muted/30 p-4">
            <Lock className="h-5 w-5 text-muted-foreground shrink-0" />
            <p className="text-sm text-muted-foreground flex-1">
                {TIER_LABELS[requiredTier]} content.{" "}
                <span className="text-foreground">
                    {TIER_DESCRIPTIONS[requiredTier]}
                </span>
            </p>
            <Button variant="outline" size="sm" onClick={onUpgradeClick}>
                {ctaText || defaultCtaText}
            </Button>
        </div>
    )
}
