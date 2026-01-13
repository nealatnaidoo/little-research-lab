import Link from "next/link"
import { Github, Twitter, Linkedin, ExternalLink } from "lucide-react"
import { PublicService, OpenAPI } from "@/lib/api"

// Ensure server-side fetching uses correct URL
OpenAPI.BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// Map social link keys to lucide icons
const socialIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  github: Github,
  twitter: Twitter,
  linkedin: Linkedin,
  x: Twitter, // X (formerly Twitter)
}

export async function PublicFooter() {
  // Fetch site settings server-side
  let siteSubtitle = ""
  let socialLinks: Record<string, string> = {}

  try {
    const settings = await PublicService.getPublicSettingsApiPublicSettingsGet()
    siteSubtitle = settings.site_subtitle
    socialLinks = settings.social_links_json || {}
  } catch (error) {
    console.error("Failed to fetch site settings for footer", error)
  }

  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t bg-background">
      <div className="container py-8 md:py-12">
        <div className="grid gap-8 md:grid-cols-2">
          {/* Left side: Site info */}
          <div>
            {siteSubtitle && (
              <p className="text-sm text-muted-foreground mb-4">
                {siteSubtitle}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              © {currentYear} Little Research Lab. All rights reserved.
            </p>
          </div>

          {/* Right side: Social links */}
          {Object.keys(socialLinks).length > 0 && (
            <div className="flex items-start justify-end">
              <div>
                <h3 className="text-sm font-semibold mb-3">Connect</h3>
                <div className="flex space-x-4">
                  {Object.entries(socialLinks).map(([key, url]) => {
                    const Icon = socialIcons[key.toLowerCase()] || ExternalLink
                    return (
                      <a
                        key={key}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground transition-colors"
                        aria-label={key}
                      >
                        <Icon className="h-5 w-5" />
                      </a>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </footer>
  )
}
