"use client"

import { useEffect } from "react"
import { OpenAPI } from "@/lib/api"

export function ApiConfig() {
    useEffect(() => {
        // Use empty BASE to proxy through Next.js rewrites (same-origin for cookies)
        OpenAPI.BASE = ""
        OpenAPI.WITH_CREDENTIALS = true // Important for HttpOnly cookies
    }, [])

    return null
}
