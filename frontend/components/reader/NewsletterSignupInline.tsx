"use client"

import { useState } from "react"
import { Mail, CheckCircle, AlertCircle, Loader2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { OpenAPI } from "@/lib/api"

interface NewsletterSignupInlineProps {
    /** Optional site name override */
    siteName?: string
    /** Optional custom heading */
    heading?: string
    /** Optional custom description */
    description?: string
    /** Compact mode for sidebar */
    compact?: boolean
}

type SubmitState = "idle" | "loading" | "success" | "error"

/**
 * Newsletter signup inline component.
 *
 * Renders a newsletter subscription form that can be placed
 * at the end of articles or in sidebars.
 *
 * Spec refs: E16.1, TA-0074, TA-0075, TA-0076
 */
export function NewsletterSignupInline({
    siteName = "Little Research Lab",
    heading = "Stay Updated",
    description = "Get new articles delivered straight to your inbox.",
    compact = false,
}: NewsletterSignupInlineProps) {
    const [email, setEmail] = useState("")
    const [submitState, setSubmitState] = useState<SubmitState>("idle")
    const [errorMessage, setErrorMessage] = useState("")

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()

        if (!email.trim()) {
            setErrorMessage("Please enter your email address")
            setSubmitState("error")
            return
        }

        // Basic email format validation
        if (!email.includes("@") || !email.split("@")[1]?.includes(".")) {
            setErrorMessage("Please enter a valid email address")
            setSubmitState("error")
            return
        }

        setSubmitState("loading")
        setErrorMessage("")

        try {
            const baseUrl = OpenAPI.BASE || "http://localhost:8000"
            const response = await fetch(
                `${baseUrl}/api/public/newsletter/subscribe`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ email }),
                }
            )

            if (response.status === 429) {
                setErrorMessage("Too many attempts. Please try again later.")
                setSubmitState("error")
                return
            }

            if (response.status === 400) {
                const data = await response.json()
                setErrorMessage(data.detail || "Unable to subscribe")
                setSubmitState("error")
                return
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }

            setSubmitState("success")
            setEmail("")
            toast.success("Please check your email to confirm your subscription")
        } catch (error) {
            console.error("Newsletter signup error:", error)
            setErrorMessage("Something went wrong. Please try again.")
            setSubmitState("error")
        }
    }

    // Success state
    if (submitState === "success") {
        return (
            <div
                className={`rounded-lg border border-green-200 bg-green-50 p-6 dark:border-green-900 dark:bg-green-900/20 ${compact ? "text-center" : ""}`}
                data-testid="newsletter-success"
            >
                <div className="flex items-center justify-center gap-2 mb-2">
                    <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                    <span className="font-medium text-green-800 dark:text-green-300">
                        Check your inbox!
                    </span>
                </div>
                <p className="text-sm text-green-700 dark:text-green-400 text-center">
                    We&apos;ve sent a confirmation link to your email.
                </p>
                <Button
                    variant="link"
                    size="sm"
                    className="mt-2 text-green-700 dark:text-green-400"
                    onClick={() => setSubmitState("idle")}
                >
                    Subscribe another email
                </Button>
            </div>
        )
    }

    // Compact mode (for sidebar)
    if (compact) {
        return (
            <div
                className="rounded-lg border bg-muted/50 p-4"
                data-testid="newsletter-signup-compact"
            >
                <div className="flex items-center gap-2 mb-2">
                    <Mail className="h-4 w-4 text-primary" />
                    <span className="font-medium text-sm">{heading}</span>
                </div>
                <form onSubmit={handleSubmit} className="space-y-2">
                    <Input
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        disabled={submitState === "loading"}
                        className="h-9 text-sm"
                        data-testid="newsletter-email"
                    />
                    <Button
                        type="submit"
                        size="sm"
                        className="w-full"
                        disabled={submitState === "loading"}
                        data-testid="newsletter-submit"
                    >
                        {submitState === "loading" ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            "Subscribe"
                        )}
                    </Button>
                    {submitState === "error" && (
                        <p className="text-xs text-destructive flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {errorMessage}
                        </p>
                    )}
                </form>
            </div>
        )
    }

    // Full mode (end of article)
    return (
        <div
            className="rounded-lg border bg-muted/30 p-6 md:p-8 my-8"
            data-testid="newsletter-signup"
        >
            <div className="max-w-md mx-auto text-center">
                <div className="flex items-center justify-center gap-2 mb-3">
                    <Mail className="h-6 w-6 text-primary" />
                    <h3 className="text-xl font-semibold">{heading}</h3>
                </div>
                <p className="text-muted-foreground mb-6">{description}</p>

                <form
                    onSubmit={handleSubmit}
                    className="flex flex-col sm:flex-row gap-3"
                >
                    <Input
                        type="email"
                        placeholder="Enter your email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        disabled={submitState === "loading"}
                        className="flex-1"
                        data-testid="newsletter-email"
                    />
                    <Button
                        type="submit"
                        disabled={submitState === "loading"}
                        data-testid="newsletter-submit"
                    >
                        {submitState === "loading" ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Subscribing...
                            </>
                        ) : (
                            "Subscribe"
                        )}
                    </Button>
                </form>

                {submitState === "error" && (
                    <p className="text-sm text-destructive flex items-center justify-center gap-1 mt-3">
                        <AlertCircle className="h-4 w-4" />
                        {errorMessage}
                    </p>
                )}

                <p className="text-xs text-muted-foreground mt-4">
                    No spam. Unsubscribe anytime.
                </p>
            </div>
        </div>
    )
}

export default NewsletterSignupInline
