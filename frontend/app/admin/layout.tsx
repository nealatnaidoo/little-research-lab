"use client"

import { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import Link from "next/link"
import {
    LayoutDashboard,
    FileText,
    Image as ImageIcon,
    Settings,
    LogOut,
    Menu,
    ChevronLeft
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuItem,
    SidebarMenuButton,
    SidebarProvider,
    SidebarTrigger,
    SidebarGroup,
    SidebarGroupLabel
} from "@/components/ui/sidebar"
import { AuthService } from "@/lib/api"
import { toast } from "sonner"

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const router = useRouter()
    const pathname = usePathname()
    const [authorized, setAuthorized] = useState(false)

    useEffect(() => {
        const checkAuth = async () => {
            try {
                await AuthService.readUsersMeApiAuthMeGet()
                setAuthorized(true)
            } catch (error) {
                toast.error("Session expired. Please login.")
                router.push("/login")
            }
        }
        checkAuth()
    }, [router])

    const handleLogout = async () => {
        try {
            await AuthService.logoutApiAuthLogoutPost()
            toast.success("Logged out")
            router.push("/login")
        } catch (error) {
            console.error("Logout failed", error)
        }
    }

    if (!authorized) {
        return <div className="flex h-screen items-center justify-center">Loading Admin...</div>
    }

    return (
        <SidebarProvider>
            <div className="flex min-h-screen w-full">
                <Sidebar>
                    <SidebarHeader>
                        <div className="px-4 py-2 font-bold text-lg text-primary">Little Research Lab</div>
                    </SidebarHeader>
                    <SidebarContent>
                        <SidebarGroup>
                            <SidebarGroupLabel>Platform</SidebarGroupLabel>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton asChild isActive={pathname === "/admin"}>
                                        <Link href="/admin">
                                            <LayoutDashboard />
                                            <span>Dashboard</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                                <SidebarMenuItem>
                                    <SidebarMenuButton asChild isActive={pathname.startsWith("/admin/content")}>
                                        <Link href="/admin/content">
                                            <FileText />
                                            <span>Content</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                                <SidebarMenuItem>
                                    <SidebarMenuButton asChild isActive={pathname.startsWith("/admin/assets")}>
                                        <Link href="/admin/assets">
                                            <ImageIcon />
                                            <span>Assets</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarGroup>

                        <SidebarGroup>
                            <SidebarGroupLabel>System</SidebarGroupLabel>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton asChild isActive={pathname.startsWith("/admin/settings")}>
                                        <Link href="/admin/settings">
                                            <Settings />
                                            <span>Settings</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarGroup>
                    </SidebarContent>
                    <SidebarFooter>
                        <SidebarMenu>
                            <SidebarMenuItem>
                                <SidebarMenuButton onClick={handleLogout}>
                                    <LogOut />
                                    <span>Logout</span>
                                </SidebarMenuButton>
                            </SidebarMenuItem>
                        </SidebarMenu>
                    </SidebarFooter>
                </Sidebar>

                <main className="flex-1 overflow-auto bg-sidebar-accent/10">
                    <header className="flex h-16 items-center gap-4 border-b bg-background px-6 shadow-sm">
                        <SidebarTrigger />
                        <div className="font-medium">Admin Workspace</div>
                    </header>
                    <div className="p-6">
                        {children}
                    </div>
                </main>
            </div>
        </SidebarProvider>
    )
}
