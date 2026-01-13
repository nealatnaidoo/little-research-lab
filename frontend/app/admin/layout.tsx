"use client"

import { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import Link from "next/link"
import {
    LayoutDashboard,
    FileText,
    Image as ImageIcon,
    Link2,
    Users,
    Settings,
    LogOut,
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
import { ThemeToggle } from "@/components/layout/ThemeToggle"
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
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="text-muted-foreground">Loading...</div>
            </div>
        )
    }

    return (
        <SidebarProvider>
            <div className="flex min-h-screen w-full">
                <Sidebar>
                    <SidebarHeader className="border-b py-4">
                        <div className="px-4">
                            {/* Subtle retro branding */}
                            <div className="font-arcade text-[8px] text-primary tracking-widest">
                                LITTLE RESEARCH LAB
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                                Admin
                            </div>
                        </div>
                    </SidebarHeader>
                    <SidebarContent className="py-4">
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
                                <SidebarMenuItem>
                                    <SidebarMenuButton asChild isActive={pathname.startsWith("/admin/links")}>
                                        <Link href="/admin/links">
                                            <Link2 />
                                            <span>Links</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                                <SidebarMenuItem>
                                    <SidebarMenuButton asChild isActive={pathname.startsWith("/admin/users")}>
                                        <Link href="/admin/users">
                                            <Users />
                                            <span>Users</span>
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
                    <SidebarFooter className="border-t py-4">
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

                <main className="flex-1 overflow-auto">
                    <header className="flex h-14 items-center gap-4 border-b bg-background px-6">
                        <SidebarTrigger />
                        <div className="flex-1" />
                        <ThemeToggle />
                    </header>
                    <div className="p-6">
                        {children}
                    </div>
                </main>
            </div>
        </SidebarProvider>
    )
}
