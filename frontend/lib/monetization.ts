/**
 * Monetization utilities for tier-based access control.
 *
 * Implements server-side enforcement (I10) and prevents client-side bypass (R8).
 * For MVP, all users have "free" entitlement via PaymentStubAdapter.
 */

export type ContentTier = "free" | "premium" | "subscriber_only"
export type EntitlementLevel = "free" | "premium" | "subscriber"

/**
 * Mapping of entitlement levels to accessible content tiers.
 */
const ENTITLEMENT_ACCESS: Record<EntitlementLevel, ContentTier[]> = {
    free: ["free"],
    premium: ["free", "premium"],
    subscriber: ["free", "premium", "subscriber_only"],
}

/**
 * Default preview blocks configuration by content tier.
 */
const DEFAULT_PREVIEW_BLOCKS: Record<ContentTier, number | null> = {
    free: null, // No limit
    premium: 3, // Show 3 blocks as preview
    subscriber_only: 2, // Show 2 blocks as preview
}

/**
 * Check if an entitlement level can access a content tier.
 */
export function canAccessTier(
    entitlement: EntitlementLevel,
    contentTier: ContentTier
): boolean {
    const accessibleTiers = ENTITLEMENT_ACCESS[entitlement] || ["free"]
    return accessibleTiers.includes(contentTier)
}

/**
 * Calculate the number of preview blocks to show.
 * Returns null if user has full access.
 */
export function calculatePreviewBlocks(
    contentTier: ContentTier,
    totalBlocks: number,
    userEntitlement: EntitlementLevel = "free"
): { previewCount: number | null; isLimited: boolean; hiddenBlocks: number } {
    // Check if user has full access
    if (canAccessTier(userEntitlement, contentTier)) {
        return {
            previewCount: null,
            isLimited: false,
            hiddenBlocks: 0,
        }
    }

    // Get preview count for this tier
    const previewCount = DEFAULT_PREVIEW_BLOCKS[contentTier] ?? 3

    return {
        previewCount: Math.min(previewCount, totalBlocks),
        isLimited: true,
        hiddenBlocks: Math.max(0, totalBlocks - previewCount),
    }
}

/**
 * Access check result for rendering decisions.
 */
export interface AccessCheckResult {
    hasFullAccess: boolean
    previewBlocks: number | null
    hiddenBlocks: number
    requiredTier: ContentTier
}

/**
 * Check access for content and determine rendering parameters.
 */
export function checkContentAccess(
    contentTier: ContentTier | undefined,
    totalBlocks: number,
    userEntitlement: EntitlementLevel = "free"
): AccessCheckResult {
    // Default to free tier if not specified
    const tier = contentTier || "free"

    const hasFullAccess = canAccessTier(userEntitlement, tier)

    if (hasFullAccess) {
        return {
            hasFullAccess: true,
            previewBlocks: null,
            hiddenBlocks: 0,
            requiredTier: tier,
        }
    }

    const { previewCount, hiddenBlocks } = calculatePreviewBlocks(
        tier,
        totalBlocks,
        userEntitlement
    )

    return {
        hasFullAccess: false,
        previewBlocks: previewCount,
        hiddenBlocks,
        requiredTier: tier,
    }
}

/**
 * Filter content blocks based on access.
 * Server-side enforcement (I10) - never send hidden blocks to client.
 */
export function filterContentBlocks<T>(
    blocks: T[],
    contentTier: ContentTier | undefined,
    userEntitlement: EntitlementLevel = "free"
): { visibleBlocks: T[]; totalBlocks: number; hiddenBlocks: number; isPreview: boolean } {
    const tier = contentTier || "free"
    const totalBlocks = blocks.length

    if (canAccessTier(userEntitlement, tier)) {
        return {
            visibleBlocks: blocks,
            totalBlocks,
            hiddenBlocks: 0,
            isPreview: false,
        }
    }

    const previewCount = DEFAULT_PREVIEW_BLOCKS[tier] ?? 3
    const visibleBlocks = blocks.slice(0, previewCount)

    return {
        visibleBlocks,
        totalBlocks,
        hiddenBlocks: totalBlocks - visibleBlocks.length,
        isPreview: true,
    }
}
