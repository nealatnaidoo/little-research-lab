"use client"

import { useEffect, useRef, useCallback } from "react"

interface EngagementData {
  contentId: string
  path: string
  timeOnPage: number // seconds
  scrollDepth: number // 0-100
}

interface UseEngagementTrackingOptions {
  contentId: string
  path: string
  enabled?: boolean
  apiEndpoint?: string
}

/**
 * Track user engagement (time on page + scroll depth) for analytics.
 *
 * Privacy: Only bucketed data is stored server-side (TA-0060).
 * This hook sends raw values; the backend buckets before storage.
 *
 * Sends data on:
 * - Page visibility change (tab switch/close)
 * - beforeunload (page navigation)
 */
export function useEngagementTracking({
  contentId,
  path,
  enabled = true,
  apiEndpoint = "/a/event",
}: UseEngagementTrackingOptions) {
  // Track time on page
  const startTimeRef = useRef<number>(Date.now())
  const visibleTimeRef = useRef<number>(0)
  const lastVisibleRef = useRef<number>(Date.now())
  const isVisibleRef = useRef<boolean>(true)

  // Track scroll depth
  const maxScrollDepthRef = useRef<number>(0)

  // Track if we've already sent data (prevent double-send)
  const hasSentRef = useRef<boolean>(false)

  // Calculate current scroll depth
  const updateScrollDepth = useCallback(() => {
    if (typeof window === "undefined") return

    const scrollTop = window.scrollY
    const docHeight = document.documentElement.scrollHeight - window.innerHeight

    if (docHeight <= 0) {
      maxScrollDepthRef.current = 100
      return
    }

    const currentDepth = Math.min(100, Math.max(0, (scrollTop / docHeight) * 100))
    if (currentDepth > maxScrollDepthRef.current) {
      maxScrollDepthRef.current = currentDepth
    }
  }, [])

  // Update visible time tracking
  const updateVisibleTime = useCallback(() => {
    if (isVisibleRef.current) {
      const now = Date.now()
      visibleTimeRef.current += (now - lastVisibleRef.current) / 1000
      lastVisibleRef.current = now
    }
  }, [])

  // Send engagement data to backend
  const sendEngagementData = useCallback(() => {
    if (!enabled || hasSentRef.current) return
    if (!contentId) return

    // Update final visible time
    updateVisibleTime()

    const data: EngagementData = {
      contentId,
      path,
      timeOnPage: Math.round(visibleTimeRef.current),
      scrollDepth: Math.round(maxScrollDepthRef.current),
    }

    // Only send if there's meaningful engagement (at least 1 second)
    if (data.timeOnPage < 1) return

    hasSentRef.current = true

    // Use sendBeacon for reliable delivery on page unload
    const payload = JSON.stringify({
      event_type: "page_view",
      ts: new Date().toISOString(),
      path: data.path,
      content_id: data.contentId,
      time_on_page: data.timeOnPage,
      scroll_depth: data.scrollDepth,
    })

    // Try sendBeacon first (works on page unload)
    if (navigator.sendBeacon) {
      const blob = new Blob([payload], { type: "application/json" })
      navigator.sendBeacon(apiEndpoint, blob)
    } else {
      // Fallback to fetch (may not complete on unload)
      fetch(apiEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
        keepalive: true,
      }).catch(() => {
        // Ignore errors - best effort
      })
    }
  }, [enabled, contentId, path, apiEndpoint, updateVisibleTime])

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return

    // Reset on mount
    startTimeRef.current = Date.now()
    lastVisibleRef.current = Date.now()
    visibleTimeRef.current = 0
    maxScrollDepthRef.current = 0
    hasSentRef.current = false
    isVisibleRef.current = !document.hidden

    // Initial scroll depth
    updateScrollDepth()

    // Scroll tracking (throttled via requestAnimationFrame)
    let scrollTicking = false
    const handleScroll = () => {
      if (!scrollTicking) {
        requestAnimationFrame(() => {
          updateScrollDepth()
          scrollTicking = false
        })
        scrollTicking = true
      }
    }

    // Visibility change tracking
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Page became hidden - update visible time and send data
        updateVisibleTime()
        isVisibleRef.current = false
        sendEngagementData()
      } else {
        // Page became visible - reset timer
        lastVisibleRef.current = Date.now()
        isVisibleRef.current = true
        // Allow re-sending if user comes back
        hasSentRef.current = false
      }
    }

    // Before unload - last chance to send
    const handleBeforeUnload = () => {
      sendEngagementData()
    }

    // Add listeners
    window.addEventListener("scroll", handleScroll, { passive: true })
    document.addEventListener("visibilitychange", handleVisibilityChange)
    window.addEventListener("beforeunload", handleBeforeUnload)

    // Cleanup
    return () => {
      window.removeEventListener("scroll", handleScroll)
      document.removeEventListener("visibilitychange", handleVisibilityChange)
      window.removeEventListener("beforeunload", handleBeforeUnload)

      // Send on unmount (navigation within SPA)
      sendEngagementData()
    }
  }, [enabled, updateScrollDepth, updateVisibleTime, sendEngagementData])

  // Return current values for debugging/display
  return {
    getTimeOnPage: () => {
      updateVisibleTime()
      return Math.round(visibleTimeRef.current)
    },
    getScrollDepth: () => Math.round(maxScrollDepthRef.current),
  }
}
