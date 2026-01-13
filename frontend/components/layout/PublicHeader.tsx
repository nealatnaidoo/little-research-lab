import Link from "next/link"
import { PublicService, OpenAPI } from "@/lib/api"
import { ThemeToggle } from "./ThemeToggle"

// Ensure server-side fetching uses correct URL
OpenAPI.BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function PublicHeader() {
  // Fetch site settings server-side
  let siteTitle = "Little Research Lab"
  try {
    const settings = await PublicService.getPublicSettingsApiPublicSettingsGet()
    siteTitle = settings.site_title
  } catch (error) {
    console.error("Failed to fetch site settings", error)
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 flex">
          <Link href="/" className="mr-6 flex items-center space-x-2">
            <span className="font-bold">{siteTitle}</span>
          </Link>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <Link
              href="/"
              className="transition-colors hover:text-foreground/80 text-foreground"
            >
              Home
            </Link>
          </nav>
        </div>
        <div className="flex flex-1 items-center justify-end space-x-2">
          <nav className="flex items-center space-x-2">
            <Link
              href="/login"
              className="text-sm font-medium transition-colors hover:text-foreground/80 text-muted-foreground"
            >
              Admin Login
            </Link>
            <ThemeToggle />
          </nav>
        </div>
      </div>
    </header>
  )
}
