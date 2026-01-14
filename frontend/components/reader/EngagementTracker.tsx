"use client"

import { useEngagementTracking } from "@/hooks/useEngagementTracking"

interface EngagementTrackerProps {
  contentId: string
  path: string
  enabled?: boolean
}

/**
 * Client component that tracks engagement for a piece of content.
 * Renders nothing - just activates the tracking hook.
 */
export function EngagementTracker({
  contentId,
  path,
  enabled = true,
}: EngagementTrackerProps) {
  useEngagementTracking({
    contentId,
    path,
    enabled,
    apiEndpoint: process.env.NEXT_PUBLIC_API_URL
      ? `${process.env.NEXT_PUBLIC_API_URL}/a/event`
      : "/a/event",
  })

  // This component renders nothing
  return null
}
