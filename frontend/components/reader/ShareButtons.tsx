"use client"

import * as React from "react"
import { useState, useCallback, useEffect } from "react"
import { Share2, Twitter, Linkedin, Facebook, Link2, Check } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

type SharingPlatform = "twitter" | "linkedin" | "facebook" | "native"

interface ShareButtonsProps {
  contentId: string
  slug: string
  title: string
  className?: string
}

interface ShareUrlResponse {
  share_url: string
  platform: string
  utm_source: string
  utm_medium: string
  utm_campaign: string
}

// Platform configuration
const PLATFORM_CONFIG: Record<SharingPlatform, {
  label: string
  icon: React.ComponentType<{ className?: string }>
  color?: string
}> = {
  twitter: {
    label: "Twitter / X",
    icon: Twitter,
    color: "hover:text-[#1DA1F2]",
  },
  linkedin: {
    label: "LinkedIn",
    icon: Linkedin,
    color: "hover:text-[#0A66C2]",
  },
  facebook: {
    label: "Facebook",
    icon: Facebook,
    color: "hover:text-[#1877F2]",
  },
  native: {
    label: "Copy Link",
    icon: Link2,
  },
}

// Check if native share API is available
function canUseNativeShare(): boolean {
  if (typeof navigator === "undefined") return false
  return typeof navigator.share === "function"
}

// Check if we're on a mobile device
function isMobileDevice(): boolean {
  if (typeof window === "undefined") return false
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  )
}

// Get API base URL
function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
}

export function ShareButtons({
  contentId,
  slug,
  title,
  className,
}: ShareButtonsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState<SharingPlatform | null>(null)
  const [copied, setCopied] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Generate share URL from API
  const fetchShareUrl = useCallback(async (platform: SharingPlatform): Promise<string | null> => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/public/share/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content_id: contentId,
          platform,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to generate share URL: ${response.status}`)
      }

      const data: ShareUrlResponse = await response.json()
      return data.share_url
    } catch (error) {
      console.error("Error fetching share URL:", error)
      return null
    }
  }, [contentId])

  // Handle native share (mobile)
  const handleNativeShare = useCallback(async () => {
    setIsLoading("native")
    try {
      const shareUrl = await fetchShareUrl("native")
      if (!shareUrl) {
        toast.error("Failed to generate share link")
        return
      }

      // Decode the URL for native share
      const decodedUrl = decodeURIComponent(shareUrl)

      await navigator.share({
        title: title,
        url: decodedUrl,
      })
      toast.success("Shared successfully!")
    } catch (error) {
      // User cancelled or share failed
      if ((error as Error).name !== "AbortError") {
        console.error("Share failed:", error)
      }
    } finally {
      setIsLoading(null)
      setIsOpen(false)
    }
  }, [fetchShareUrl, title])

  // Handle copy to clipboard
  const handleCopyLink = useCallback(async () => {
    setIsLoading("native")
    try {
      const shareUrl = await fetchShareUrl("native")
      if (!shareUrl) {
        toast.error("Failed to generate share link")
        return
      }

      // Decode the URL for clipboard
      const decodedUrl = decodeURIComponent(shareUrl)

      await navigator.clipboard.writeText(decodedUrl)
      setCopied(true)
      toast.success("Link copied to clipboard!")

      // Reset copied state after animation
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error("Copy failed:", error)
      toast.error("Failed to copy link")
    } finally {
      setIsLoading(null)
      setIsOpen(false)
    }
  }, [fetchShareUrl])

  // Handle social platform share (opens new window)
  const handlePlatformShare = useCallback(async (platform: SharingPlatform) => {
    if (platform === "native") {
      // On mobile with native share support, use native share
      if (canUseNativeShare() && isMobileDevice()) {
        return handleNativeShare()
      }
      // Otherwise copy to clipboard
      return handleCopyLink()
    }

    setIsLoading(platform)
    try {
      const shareUrl = await fetchShareUrl(platform)
      if (!shareUrl) {
        toast.error("Failed to generate share link")
        return
      }

      // Open share URL in new window
      const width = 600
      const height = 400
      const left = (window.innerWidth - width) / 2
      const top = (window.innerHeight - height) / 2

      window.open(
        shareUrl,
        `share_${platform}`,
        `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
      )
    } catch (error) {
      console.error("Share failed:", error)
      toast.error("Failed to open share window")
    } finally {
      setIsLoading(null)
      setIsOpen(false)
    }
  }, [fetchShareUrl, handleNativeShare, handleCopyLink])

  // Don't render until mounted (avoid hydration mismatch)
  if (!mounted) {
    return (
      <Button
        variant="outline"
        size="sm"
        className={cn("gap-2", className)}
        disabled
      >
        <Share2 className="h-4 w-4" />
        Share
      </Button>
    )
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn("gap-2", className)}
        >
          <Share2 className="h-4 w-4" />
          Share
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {/* Social platforms */}
        {(["twitter", "linkedin", "facebook"] as SharingPlatform[]).map((platform) => {
          const config = PLATFORM_CONFIG[platform]
          const Icon = config.icon
          const isLoadingThis = isLoading === platform

          return (
            <DropdownMenuItem
              key={platform}
              onClick={() => handlePlatformShare(platform)}
              disabled={isLoading !== null}
              className={cn(
                "cursor-pointer gap-3",
                config.color
              )}
            >
              <Icon className={cn("h-4 w-4", isLoadingThis && "animate-pulse")} />
              <span>{config.label}</span>
            </DropdownMenuItem>
          )
        })}

        {/* Divider */}
        <div className="my-1 h-px bg-border" />

        {/* Copy Link / Native Share */}
        <DropdownMenuItem
          onClick={() => handlePlatformShare("native")}
          disabled={isLoading !== null}
          className="cursor-pointer gap-3"
        >
          {copied ? (
            <>
              <Check className="h-4 w-4 text-green-500" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Link2 className={cn("h-4 w-4", isLoading === "native" && "animate-pulse")} />
              <span>{canUseNativeShare() && isMobileDevice() ? "Share..." : "Copy Link"}</span>
            </>
          )}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// Also export a compact version for inline use
export function ShareButtonCompact({
  contentId,
  slug,
  title,
  className,
}: ShareButtonsProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleShare = useCallback(async () => {
    setIsLoading(true)
    try {
      // Prefer native share on mobile
      if (canUseNativeShare() && isMobileDevice()) {
        const response = await fetch(`${getApiBaseUrl()}/api/public/share/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content_id: contentId, platform: "native" }),
        })
        if (response.ok) {
          const data: ShareUrlResponse = await response.json()
          await navigator.share({
            title,
            url: decodeURIComponent(data.share_url),
          })
        }
      } else {
        // Fallback to copy
        const response = await fetch(`${getApiBaseUrl()}/api/public/share/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content_id: contentId, platform: "native" }),
        })
        if (response.ok) {
          const data: ShareUrlResponse = await response.json()
          await navigator.clipboard.writeText(decodeURIComponent(data.share_url))
          setCopied(true)
          toast.success("Link copied!")
          setTimeout(() => setCopied(false), 2000)
        }
      }
    } catch (error) {
      if ((error as Error).name !== "AbortError") {
        toast.error("Failed to share")
      }
    } finally {
      setIsLoading(false)
    }
  }, [contentId, title])

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" disabled className={className}>
        <Share2 className="h-4 w-4" />
      </Button>
    )
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={handleShare}
      disabled={isLoading}
      className={className}
      title="Share"
    >
      {copied ? (
        <Check className="h-4 w-4 text-green-500" />
      ) : (
        <Share2 className={cn("h-4 w-4", isLoading && "animate-pulse")} />
      )}
    </Button>
  )
}
