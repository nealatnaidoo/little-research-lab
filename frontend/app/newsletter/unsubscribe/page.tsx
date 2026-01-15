"use client"

import { Suspense } from "react"
import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { MailX, CheckCircle, XCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { OpenAPI } from "@/lib/api"

type UnsubscribeState = "loading" | "success" | "already" | "error"

function UnsubscribeContent() {
    const searchParams = useSearchParams()
    const token = searchParams.get("token")
    const [state, setState] = useState<UnsubscribeState>("loading")
    const [message, setMessage] = useState("")

    useEffect(() => {
        if (!token) {
            setState("error")
            setMessage("Invalid unsubscribe link. Please check your email and try again.")
            return
        }

        unsubscribe(token)
    }, [token])

    async function unsubscribe(token: string) {
        try {
            const baseUrl = OpenAPI.BASE || "http://localhost:8000"
            const response = await fetch(
                `${baseUrl}/api/public/newsletter/unsubscribe?token=${encodeURIComponent(token)}`
            )

            if (!response.ok) {
                const data = await response.json()
                setState("error")
                setMessage(data.detail || "Unable to unsubscribe")
                return
            }

            const data = await response.json()
            if (data.message?.includes("already")) {
                setState("already")
                setMessage("You were already unsubscribed.")
            } else {
                setState("success")
                setMessage("You have been unsubscribed.")
            }
        } catch (error) {
            console.error("Unsubscribe error:", error)
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
                    <h1 className="text-2xl font-bold">Processing...</h1>
                    <p className="text-muted-foreground">Please wait a moment.</p>
                </>
            )}

            {/* Success state */}
            {state === "success" && (
                <>
                    <MailX className="h-16 w-16 mx-auto text-muted-foreground" />
                    <h1 className="text-2xl font-bold">Unsubscribed</h1>
                    <p className="text-muted-foreground">{message}</p>
                    <p className="text-sm text-muted-foreground">
                        Sorry to see you go! You won&apos;t receive any more emails from us.
                    </p>
                </>
            )}

            {/* Already unsubscribed state */}
            {state === "already" && (
                <>
                    <CheckCircle className="h-16 w-16 mx-auto text-muted-foreground" />
                    <h1 className="text-2xl font-bold">Already Unsubscribed</h1>
                    <p className="text-muted-foreground">{message}</p>
                </>
            )}

            {/* Error state */}
            {state === "error" && (
                <>
                    <XCircle className="h-16 w-16 mx-auto text-destructive" />
                    <h1 className="text-2xl font-bold text-destructive">
                        Unsubscribe Failed
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

export default function NewsletterUnsubscribePage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
            <Suspense fallback={<LoadingFallback />}>
                <UnsubscribeContent />
            </Suspense>
        </div>
    )
}
