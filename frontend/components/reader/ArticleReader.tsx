"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import {
  ReaderControls,
  ReadingProgressBar,
  FONT_SIZE_CLASSES,
  WIDTH_CLASSES,
  loadPreferences,
  DEFAULT_PREFERENCES,
  type ReaderPreferences,
} from "./index"

interface ArticleReaderProps {
  children: React.ReactNode
  className?: string
  showProgressBar?: boolean
  showControls?: boolean
}

export function ArticleReader({
  children,
  className,
  showProgressBar = true,
  showControls = true,
}: ArticleReaderProps) {
  const [preferences, setPreferences] = useState<ReaderPreferences>(DEFAULT_PREFERENCES)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    setPreferences(loadPreferences())
  }, [])

  // Get dynamic classes based on preferences
  const fontSizeClass = FONT_SIZE_CLASSES[preferences.fontSize]
  const widthClass = WIDTH_CLASSES[preferences.readingWidth]

  return (
    <>
      {/* Progress bar */}
      {showProgressBar && <ReadingProgressBar />}

      {/* Article content with dynamic styling */}
      <div
        className={cn(
          "transition-all duration-300 ease-out",
          mounted && widthClass,
          className
        )}
      >
        <div
          className={cn(
            "prose prose-neutral dark:prose-invert mx-auto transition-all duration-300",
            mounted && fontSizeClass,
            // Enhanced typography defaults
            "prose-headings:font-bold prose-headings:tracking-tight",
            "prose-p:leading-relaxed",
            "prose-a:text-primary prose-a:no-underline hover:prose-a:underline",
            "prose-img:rounded-lg prose-img:shadow-md",
            "prose-blockquote:border-l-primary prose-blockquote:italic",
            "prose-code:text-primary prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded",
          )}
        >
          {children}
        </div>
      </div>

      {/* Reader controls */}
      {showControls && (
        <ReaderControls onPreferencesChange={setPreferences} />
      )}
    </>
  )
}
