"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { Settings2, Type, Columns, Sun, Moon, Monitor, X } from "lucide-react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Types for reader preferences
type FontSize = "small" | "medium" | "large" | "xlarge"
type ReadingWidth = "narrow" | "standard" | "wide" | "full"

interface ReaderPreferences {
  fontSize: FontSize
  readingWidth: ReadingWidth
}

// CSS class mappings (from rules.yaml)
const FONT_SIZE_CLASSES: Record<FontSize, string> = {
  small: "prose-sm",
  medium: "prose-base",
  large: "prose-lg",
  xlarge: "prose-xl",
}

const WIDTH_CLASSES: Record<ReadingWidth, string> = {
  narrow: "max-w-prose",
  standard: "max-w-3xl",
  wide: "max-w-5xl",
  full: "max-w-full",
}

const FONT_SIZE_LABELS: Record<FontSize, string> = {
  small: "S",
  medium: "M",
  large: "L",
  xlarge: "XL",
}

const WIDTH_LABELS: Record<ReadingWidth, string> = {
  narrow: "Narrow",
  standard: "Standard",
  wide: "Wide",
  full: "Full",
}

// Storage key
const STORAGE_KEY = "reader_preferences"

// Default preferences
const DEFAULT_PREFERENCES: ReaderPreferences = {
  fontSize: "medium",
  readingWidth: "standard",
}

// Load preferences from localStorage
function loadPreferences(): ReaderPreferences {
  if (typeof window === "undefined") return DEFAULT_PREFERENCES
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return { ...DEFAULT_PREFERENCES, ...JSON.parse(stored) }
    }
  } catch {
    // Ignore parse errors
  }
  return DEFAULT_PREFERENCES
}

// Save preferences to localStorage
function savePreferences(prefs: ReaderPreferences): void {
  if (typeof window === "undefined") return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch {
    // Ignore storage errors
  }
}

interface ReaderControlsProps {
  onPreferencesChange?: (prefs: ReaderPreferences) => void
  className?: string
}

export function ReaderControls({ onPreferencesChange, className }: ReaderControlsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [preferences, setPreferences] = useState<ReaderPreferences>(DEFAULT_PREFERENCES)
  const [mounted, setMounted] = useState(false)
  const { theme, setTheme } = useTheme()

  // Load preferences on mount
  useEffect(() => {
    setMounted(true)
    const loaded = loadPreferences()
    setPreferences(loaded)
    onPreferencesChange?.(loaded)
  }, [])

  // Update parent when preferences change
  const updatePreferences = (updates: Partial<ReaderPreferences>) => {
    const newPrefs = { ...preferences, ...updates }
    setPreferences(newPrefs)
    savePreferences(newPrefs)
    onPreferencesChange?.(newPrefs)
  }

  // Don't render until mounted (avoid hydration mismatch)
  if (!mounted) {
    return (
      <Button
        variant="outline"
        size="icon"
        className={cn("fixed bottom-6 right-6 z-50 rounded-full shadow-lg", className)}
        disabled
      >
        <Settings2 className="h-5 w-5" />
      </Button>
    )
  }

  return (
    <>
      {/* Floating trigger button */}
      <Button
        variant="outline"
        size="icon"
        className={cn(
          "fixed bottom-6 right-6 z-50 rounded-full shadow-lg transition-all",
          "hover:scale-105 hover:shadow-xl",
          "bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60",
          isOpen && "rotate-45",
          className
        )}
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? "Close reader controls" : "Open reader controls"}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Settings2 className="h-5 w-5" />}
      </Button>

      {/* Controls panel */}
      <div
        className={cn(
          "fixed bottom-20 right-6 z-50 w-72 rounded-xl border bg-background/95 p-4 shadow-2xl backdrop-blur transition-all duration-300",
          "supports-[backdrop-filter]:bg-background/80",
          isOpen
            ? "translate-y-0 opacity-100"
            : "pointer-events-none translate-y-4 opacity-0"
        )}
      >
        <div className="space-y-5">
          {/* Font Size */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Type className="h-4 w-4" />
              <span>Font Size</span>
            </div>
            <div className="flex gap-1">
              {(["small", "medium", "large", "xlarge"] as FontSize[]).map((size) => (
                <Button
                  key={size}
                  variant={preferences.fontSize === size ? "default" : "outline"}
                  size="sm"
                  className={cn(
                    "flex-1 transition-all",
                    preferences.fontSize === size && "ring-2 ring-primary/20"
                  )}
                  onClick={() => updatePreferences({ fontSize: size })}
                >
                  <span className={cn(
                    size === "small" && "text-xs",
                    size === "medium" && "text-sm",
                    size === "large" && "text-base",
                    size === "xlarge" && "text-lg"
                  )}>
                    {FONT_SIZE_LABELS[size]}
                  </span>
                </Button>
              ))}
            </div>
          </div>

          {/* Reading Width */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Columns className="h-4 w-4" />
              <span>Width</span>
            </div>
            <div className="grid grid-cols-2 gap-1">
              {(["narrow", "standard", "wide", "full"] as ReadingWidth[]).map((width) => (
                <Button
                  key={width}
                  variant={preferences.readingWidth === width ? "default" : "outline"}
                  size="sm"
                  className={cn(
                    "transition-all",
                    preferences.readingWidth === width && "ring-2 ring-primary/20"
                  )}
                  onClick={() => updatePreferences({ readingWidth: width })}
                >
                  {WIDTH_LABELS[width]}
                </Button>
              ))}
            </div>
          </div>

          {/* Theme */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Sun className="h-4 w-4" />
              <span>Theme</span>
            </div>
            <div className="flex gap-1">
              <Button
                variant={theme === "light" ? "default" : "outline"}
                size="sm"
                className={cn(
                  "flex-1 transition-all",
                  theme === "light" && "ring-2 ring-primary/20"
                )}
                onClick={() => setTheme("light")}
              >
                <Sun className="mr-1.5 h-3.5 w-3.5" />
                Light
              </Button>
              <Button
                variant={theme === "dark" ? "default" : "outline"}
                size="sm"
                className={cn(
                  "flex-1 transition-all",
                  theme === "dark" && "ring-2 ring-primary/20"
                )}
                onClick={() => setTheme("dark")}
              >
                <Moon className="mr-1.5 h-3.5 w-3.5" />
                Dark
              </Button>
              <Button
                variant={theme === "system" ? "default" : "outline"}
                size="sm"
                className={cn(
                  "flex-1 transition-all",
                  theme === "system" && "ring-2 ring-primary/20"
                )}
                onClick={() => setTheme("system")}
              >
                <Monitor className="mr-1.5 h-3.5 w-3.5" />
                Auto
              </Button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

// Export utilities for use in parent components
export { FONT_SIZE_CLASSES, WIDTH_CLASSES, loadPreferences, DEFAULT_PREFERENCES }
export type { ReaderPreferences, FontSize, ReadingWidth }
