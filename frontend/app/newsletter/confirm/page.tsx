"use client"

import { Suspense } from "react"
import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { CheckCircle, XCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { OpenAPI } from "@/lib/api"

type ConfirmState = "loading" | "success" | "already" | "error"

function ConfirmContent() {
    const searchParams = useSearchParams()
    const token = searchParams.get("token")
    const [state, setState] = useState<ConfirmState>("loading")
    const [message, setMessage] = useState("")

    useEffect(() => {
        if (!token) {
            setState("error")
            setMessage("Invalid confirmation link. Please check your email and try again.")
            return
        }

        confirmSubscription(token)
    }, [token])

    async function confirmSubscription(token: string) {
        try {
            const baseUrl = OpenAPI.BASE || "http://localhost:8000"
            const response = await fetch(
                `${baseUrl}/api/public/newsletter/confirm?token=${encodeURIComponent(token)}`
            )

            if (!response.ok) {
                const data = await response.json()
                setState("error")
                setMessage(data.detail || "Unable to confirm subscription")
                return
            }

            const data = await response.json()
            if (data.message?.includes("already")) {
                setState("already")
                setMessage("Your subscription was already confirmed.")
            } else {
                setState("success")
                setMessage("Your subscription is now confirmed!")
            }
        } catch (error) {
            console.error("Confirmation error:", error)
            setState("error")
            setMessage("Something went wrong. Please try again later.")
        }
    }

    return (
        <div className="w-full max-w-md text-center space-y-6">
            {/* Loading state */}
            {state === "loading" && (
                <>
                    <Loader2 className="h-16 w-16 mx-auto animate-spin text-primary" />
                    <h1 className="text-2xl font-bold">Confirming your subscription...</h1>
                    <p className="text-muted-foreground">Please wait a moment.</p>
                </>
            )}

            {/* Success state */}
            {state === "success" && (
                <>
                    <CheckCircle className="h-16 w-16 mx-auto text-green-500" />
                    <h1 className="text-2xl font-bold text-green-700 dark:text-green-400">
                        Welcome!
                    </h1>
                    <p className="text-muted-foreground">{message}</p>
                    <p className="text-sm text-muted-foreground">
                        You&apos;ll now receive our newsletter updates.
                    </p>
                </>
            )}

            {/* Already confirmed state */}
            {state === "already" && (
                <>
                    <CheckCircle className="h-16 w-16 mx-auto text-blue-500" />
                    <h1 className="text-2xl font-bold">Already Confirmed</h1>
                    <p className="text-muted-foreground">{message}</p>
                </>
            )}

            {/* Error state */}
            {state === "error" && (
                <>
                    <XCircle className="h-16 w-16 mx-auto text-destructive" />
                    <h1 className="text-2xl font-bold text-destructive">
                        Confirmation Failed
                    </h1>
                    <p className="text-muted-foreground">{message}</p>
                </>
            )}

            {/* Back to home button */}
            {state !== "loading" && (
                <Button asChild variant="outline">
                    <Link href="/">Back to Home</Link>
                </Button>
            )}
        </div>
    )
}

function LoadingFallback() {
    return (
        <div className="w-full max-w-md text-center space-y-6">
            <Loader2 className="h-16 w-16 mx-auto animate-spin text-primary" />
            <h1 className="text-2xl font-bold">Loading...</h1>
        </div>
    )
}

export default function NewsletterConfirmPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
            <Suspense fallback={<LoadingFallback />}>
                <ConfirmContent />
            </Suspense>
        </div>
    )
}
