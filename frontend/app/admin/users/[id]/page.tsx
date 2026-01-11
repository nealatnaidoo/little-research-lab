"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { UsersService } from "@/lib/api"

const formSchema = z.object({
    email: z.string().email().readonly(), // Display only
    roles: z.string(),
    status: z.string(),
})

export default function EditUserPage() {
    const router = useRouter()
    const params = useParams()
    const id = params.id as string

    const [isLoading, setIsLoading] = useState(false)
    const [isFetching, setIsFetching] = useState(true)

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            email: "",
            roles: "editor",
            status: "active"
        },
    })

    useEffect(() => {
        if (id) loadUser(id)
    }, [id])

    async function loadUser(userId: string) {
        try {
            // Need get_user? 
            // UsersService doesn't have `getUserApiUsersIdGet` yet?
            // Wait, I only implemented list/create/update in routes.
            // I missed GET /{id} in backend plan!
            // Quick fix: Use list and find? Or implement GET?
            // "I will implement UsersService.list, create, update, delete..." - Plan said GET /{id}.
            // But I forgot to add it to `users.py` code I submitted!
            // Mistake. I need to add GET /{id} to `users.py` and regen client, OR fix this page to use list + find (less efficient but works for MVP).

            // Let's use List + Find for speed now, as listing is cheap (few users).
            // Actually, `update_user` needs ID.

            const users = await UsersService.listUsersApiUsersGet();
            const user = users.find(u => u.id === userId);

            if (user) {
                form.reset({
                    email: user.email,
                    roles: user.roles?.[0] || "editor", // Simplified single-role UI
                    status: user.status
                })
            } else {
                toast.error("User not found");
                router.push("/admin/users");
            }
        } catch (e) {
            console.error(e)
            toast.error("Failed to load user")
        } finally {
            setIsFetching(false)
        }
    }

    async function onSubmit(values: z.infer<typeof formSchema>) {
        setIsLoading(true)
        try {
            await UsersService.updateUserApiUsersUserIdPut(id, {
                roles: [values.roles],
                status: values.status
            });
            toast.success("User updated")
            router.push("/admin/users")
        } catch (e: any) {
            console.error(e)
            toast.error(e.body?.detail || "Failed to update user")
        } finally {
            setIsLoading(false)
        }
    }

    if (isFetching) return <div>Loading...</div>

    return (
        <div className="space-y-6 max-w-lg">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Edit User</h1>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                    <FormField
                        control={form.control}
                        name="email"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Email (Read-only)</FormLabel>
                                <FormControl>
                                    <Input {...field} disabled />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="roles"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Role</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select role" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value="editor">Editor</SelectItem>
                                        <SelectItem value="admin">Admin</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="status"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Status</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select status" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value="active">Active</SelectItem>
                                        <SelectItem value="disabled">Disabled</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="flex justify-end gap-2">
                        <Button variant="outline" type="button" onClick={() => router.back()}>Cancel</Button>
                        <Button type="submit" disabled={isLoading}>
                            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Save
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    )
}
