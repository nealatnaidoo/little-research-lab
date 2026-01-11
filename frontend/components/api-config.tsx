"use client"

import { useEffect } from "react"
import { OpenAPI } from "@/lib/api"

export function ApiConfig() {
    useEffect(() => {
        // In dev, assuming NEXT_PUBLIC_API_URL or default to localhost:8000
        OpenAPI.BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        OpenAPI.WITH_CREDENTIALS = true // Important for HttpOnly cookies
    }, [])

    return null
}
