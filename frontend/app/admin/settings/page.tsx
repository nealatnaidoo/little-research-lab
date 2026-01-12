"use client"

import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { SettingsService, type SettingsFormData } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"

export default function SettingsPage() {
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const form = useForm<SettingsFormData>()

    // Social links helper state - for simplicity mapping specific known keys, 
    // but the API supports arbitrary keys. adhering to common ones for now.
    const socialKeys = ["twitter", "github", "linkedin"]

    useEffect(() => {
        SettingsService.getSettings()
            .then((data) => {
                form.reset({
                    site_title: data.site_title,
                    site_subtitle: data.site_subtitle,
                    avatar_asset_id: data.avatar_asset_id,
                    theme: data.theme,
                    social_links_json: data.social_links_json,
                })
                setLoading(false)
            })
            .catch(() => {
                toast.error("Failed to load settings")
                setLoading(false)
            })
    }, [form.reset])

    const onSubmit = async (data: SettingsFormData) => {
        setSaving(true)
        try {
            await SettingsService.updateSettings(data)
            toast.success("Settings saved")
        } catch (err) {
            console.error(err)
            toast.error("Failed to save settings")
        } finally {
            setSaving(false)
        }
    }

    if (loading) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-10 w-48" />
                <div className="grid gap-6">
                    <Skeleton className="h-[200px] w-full" />
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold">Settings</h1>
                <p className="text-muted-foreground">Manage your site configuration.</p>
            </div>

            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                <Card>
                    <CardHeader>
                        <CardTitle>Site Configuration</CardTitle>
                        <CardDescription>
                            Configure core site metadata.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="site_title">Site Title</Label>
                            <Input
                                id="site_title"
                                data-testid="settings-site-title"
                                {...form.register("site_title", { required: true })}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="site_subtitle">Subtitle / Tagline</Label>
                            <Input
                                id="site_subtitle"
                                {...form.register("site_subtitle")}
                            />
                        </div>

                        {/* Theme Select could go here, sticking to simple inputs for now */}
                        <div className="space-y-2">
                            <Label htmlFor="theme">Theme (light/dark/system)</Label>
                            <Input
                                id="theme"
                                {...form.register("theme")}
                            />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Social Links</CardTitle>
                        <CardDescription>
                            Links to display in valid locations on the public site.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {socialKeys.map((key) => (
                            <div key={key} className="space-y-2">
                                <Label htmlFor={`social_${key}`} className="capitalize">{key}</Label>
                                <Input
                                    id={`social_${key}`}
                                    {...form.register(`social_links_json.${key}`)}
                                    placeholder={`https://${key}.com/...`}
                                />
                            </div>
                        ))}
                    </CardContent>
                </Card>

                <div className="flex justify-end">
                    <Button type="submit" disabled={saving} data-testid="settings-save">
                        {saving ? "Saving..." : "Save Changes"}
                    </Button>
                </div>
            </form>
        </div>
    )
}
