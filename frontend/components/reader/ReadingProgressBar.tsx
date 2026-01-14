"use client"

import * as React from "react"
import { useState, useEffect, useCallback } from "react"
import { cn } from "@/lib/utils"

interface ReadingProgressBarProps {
  className?: string
  color?: string
  height?: number
}

export function ReadingProgressBar({
  className,
  color = "hsl(var(--primary))",
  height = 3,
}: ReadingProgressBarProps) {
  const [progress, setProgress] = useState(0)
  const [mounted, setMounted] = useState(false)

  const updateProgress = useCallback(() => {
    const scrollTop = window.scrollY
    const docHeight = document.documentElement.scrollHeight - window.innerHeight

    if (docHeight <= 0) {
      setProgress(100)
      return
    }

    const scrollPercent = (scrollTop / docHeight) * 100
    setProgress(Math.min(100, Math.max(0, scrollPercent)))
  }, [])

  useEffect(() => {
    setMounted(true)

    // Initial calculation
    updateProgress()

    // Use requestAnimationFrame for smooth updates
    let ticking = false
    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          updateProgress()
          ticking = false
        })
        ticking = true
      }
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    window.addEventListener("resize", updateProgress, { passive: true })

    return () => {
      window.removeEventListener("scroll", handleScroll)
      window.removeEventListener("resize", updateProgress)
    }
  }, [updateProgress])

  // Don't render on server
  if (!mounted) {
    return null
  }

  return (
    <div
      className={cn(
        "fixed top-0 left-0 right-0 z-[100] pointer-events-none",
        className
      )}
      style={{ height: `${height}px` }}
      role="progressbar"
      aria-valuenow={Math.round(progress)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Reading progress"
    >
      <div
        className="h-full transition-[width] duration-150 ease-out"
        style={{
          width: `${progress}%`,
          backgroundColor: color,
        }}
      />
    </div>
  )
}
