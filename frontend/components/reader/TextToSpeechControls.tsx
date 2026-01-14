"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Play, Pause, Square, Volume2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Slider } from "@/components/ui/slider"

type TTSState = "stopped" | "playing" | "paused"

interface TextToSpeechControlsProps {
  /** Text content to read aloud */
  text: string
  /** Optional class name */
  className?: string
}

/**
 * Text-to-Speech controls with feature detection.
 *
 * Spec refs: E13.2, TA-0054, TA-0055, HV7
 *
 * Gracefully degrades if speechSynthesis is unavailable (returns null).
 * Cancels speech on unmount to prevent orphaned audio.
 */
export function TextToSpeechControls({ text, className }: TextToSpeechControlsProps) {
  const [isSupported, setIsSupported] = useState<boolean | null>(null)
  const [state, setState] = useState<TTSState>("stopped")
  const [rate, setRate] = useState(1)
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([])
  const [selectedVoice, setSelectedVoice] = useState<string>("")
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  // Check for speechSynthesis support on mount
  useEffect(() => {
    const supported = typeof window !== "undefined" && "speechSynthesis" in window
    setIsSupported(supported)

    if (supported) {
      // Load voices (may be async on some browsers)
      const loadVoices = () => {
        const availableVoices = window.speechSynthesis.getVoices()
        // Filter to English voices for simplicity
        const englishVoices = availableVoices.filter(v => v.lang.startsWith("en"))
        setVoices(englishVoices.length > 0 ? englishVoices : availableVoices)
        if (englishVoices.length > 0 && !selectedVoice) {
          setSelectedVoice(englishVoices[0].name)
        }
      }

      loadVoices()
      // Chrome loads voices asynchronously
      window.speechSynthesis.onvoiceschanged = loadVoices
    }

    // Cleanup: cancel any ongoing speech on unmount
    return () => {
      if (supported) {
        window.speechSynthesis.cancel()
      }
    }
  }, [selectedVoice])

  const play = useCallback(() => {
    if (!isSupported || !text) return

    // If paused, resume
    if (state === "paused") {
      window.speechSynthesis.resume()
      setState("playing")
      return
    }

    // Cancel any existing speech
    window.speechSynthesis.cancel()

    // Create new utterance
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = rate

    // Set voice if selected
    if (selectedVoice) {
      const voice = voices.find(v => v.name === selectedVoice)
      if (voice) utterance.voice = voice
    }

    // Event handlers
    utterance.onend = () => setState("stopped")
    utterance.onerror = () => setState("stopped")

    utteranceRef.current = utterance
    window.speechSynthesis.speak(utterance)
    setState("playing")
  }, [isSupported, text, state, rate, selectedVoice, voices])

  const pause = useCallback(() => {
    if (!isSupported) return
    window.speechSynthesis.pause()
    setState("paused")
  }, [isSupported])

  const stop = useCallback(() => {
    if (!isSupported) return
    window.speechSynthesis.cancel()
    setState("stopped")
  }, [isSupported])

  // Graceful degradation: return null if not supported (HV7)
  if (isSupported === null) {
    // Still checking support
    return null
  }

  if (!isSupported) {
    // Not supported - degrade gracefully
    return null
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={className}
          aria-label="Text to speech controls"
        >
          <Volume2 className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64" align="end">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Listen to Article</span>
            <div className="flex gap-1">
              {state === "playing" ? (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={pause}
                  aria-label="Pause"
                >
                  <Pause className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={play}
                  aria-label="Play"
                >
                  <Play className="h-4 w-4" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={stop}
                disabled={state === "stopped"}
                aria-label="Stop"
              >
                <Square className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Speed</span>
              <span className="text-xs text-muted-foreground">{rate}x</span>
            </div>
            <Slider
              value={[rate]}
              onValueChange={([value]) => setRate(value)}
              min={0.5}
              max={2}
              step={0.25}
              disabled={state === "playing"}
            />
          </div>

          {voices.length > 1 && (
            <div className="space-y-2">
              <span className="text-xs text-muted-foreground">Voice</span>
              <select
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                disabled={state === "playing"}
                className="w-full rounded-md border bg-background px-2 py-1 text-sm"
              >
                {voices.map((voice) => (
                  <option key={voice.name} value={voice.name}>
                    {voice.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {state !== "stopped" && (
            <p className="text-xs text-muted-foreground">
              {state === "playing" ? "Playing..." : "Paused"}
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
