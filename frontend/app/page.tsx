import Link from "next/link";
import { PublicService } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { OpenAPI } from "@/lib/api";

// Types for public content
interface PublicPost {
  id: string;
  title: string;
  slug: string;
  summary?: string;
  publish_at?: string;
  created_at: string;
}

interface PublicLink {
  id: string;
  title: string;
  url: string;
}

// Force dynamic rendering - no caching so content updates appear immediately
export const dynamic = 'force-dynamic';

// Ensure Server Components use the right base URL
OpenAPI.BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default async function Home() {
  // Fetch public data
  // Note: we might need try/catch if backend is down
  let data = null;
  try {
    data = await PublicService.getPublicHomeApiPublicHomeGet();
  } catch (e) {
    console.error("Failed to fetch home data", e);
  }

  const posts = data?.posts || [];
  const links = data?.links || [];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-12 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-primary">
            Little Research Lab
          </h1>
          <p className="mt-4 text-muted-foreground text-lg">
            Experiments, thoughts, and digital gardening.
          </p>
          <div className="mt-6">
            <Link href="/login" className="text-sm text-muted-foreground hover:underline">
              Admin Login
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-8 md:grid-cols-[1fr_300px]">
          {/* Main Content: Posts */}
          <div className="space-y-6">
            <h2 className="text-2xl font-semibold">Latest Notes</h2>
            {posts.length === 0 ? (
              <p className="text-muted-foreground">No posts found.</p>
            ) : (
              posts.map((post: PublicPost) => (
                <Card key={post.id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle>
                      <Link href={`/p/${post.slug}`} className="hover:text-primary">
                        {post.title}
                      </Link>
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {new Date(post.publish_at || post.created_at).toLocaleDateString()}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <p className="line-clamp-3 text-muted-foreground">
                      {post.summary || "No summary available."}
                    </p>
                  </CardContent>
                </Card>
              ))
            )}
          </div>

          {/* Sidebar: Links */}
          <aside className="space-y-6">
            <div className="rounded-lg border bg-card p-6">
              <h3 className="font-semibold mb-4 text-lg">Elsewhere</h3>
              {links.length === 0 ? (
                <p className="text-muted-foreground text-sm">No links yet.</p>
              ) : (
                <ul className="space-y-3">
                  {links.map((link: PublicLink) => (
                    <li key={link.id}>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium hover:underline text-primary"
                      >
                        {link.title}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
