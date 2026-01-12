import Link from "next/link"
import {
    FileText,
    Plus,
    Upload,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"

export default function AdminPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
                <p className="text-muted-foreground">Welcome back to the lab.</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                    <CardHeader>
                        <CardTitle>Quick Actions</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Button asChild className="w-full justify-start">
                            <Link href="/admin/content/new">
                                <Plus className="mr-2 h-4 w-4" />
                                New Post
                            </Link>
                        </Button>
                        <Button asChild variant="outline" className="w-full justify-start">
                            <Link href="/admin/assets">
                                <Upload className="mr-2 h-4 w-4" />
                                Upload Asset
                            </Link>
                        </Button>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Content</CardTitle>
                        <CardDescription>Recent activity</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-semibold text-primary">--</div>
                        <p className="text-xs text-muted-foreground mt-1">Total items</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
