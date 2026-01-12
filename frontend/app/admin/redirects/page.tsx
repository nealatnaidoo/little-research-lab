"use client"

import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2, Plus, Pencil, Trash2, AlertTriangle, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Switch } from "@/components/ui/switch"
import { RedirectService, type RedirectResponse } from "@/lib/api"

const formSchema = z.object({
    source_path: z.string().startsWith("/", "Path must start with /"),
    target_path: z.string().startsWith("/", "Path must start with /"),
    status_code: z.coerce.number().refine((val) => [301, 302].includes(val), {
        message: "Status code must be 301 or 302",
    }),
    notes: z.string().optional(),
    enabled: z.boolean().default(true),
})

export default function RedirectsPage() {
    const [redirects, setRedirects] = useState<RedirectResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [dialogOpen, setDialogOpen] = useState(false)
    const [editingId, setEditingId] = useState<string | null>(null)
    const [validationIssues, setValidationIssues] = useState<any[]>([])

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema) as any,
        defaultValues: {
            source_path: "",
            target_path: "",
            status_code: 301,
            notes: "",
            enabled: true,
        },
    })

    useEffect(() => {
        fetchRedirects()
    }, [])

    async function fetchRedirects() {
        setLoading(true)
        try {
            const data = await RedirectService.list()
            setRedirects(data.redirects)

            // Also validate
            const validation = await RedirectService.validate()
            setValidationIssues(validation.issues || [])

        } catch (error) {
            console.error(error)
            toast.error("Failed to load redirects")
        } finally {
            setLoading(false)
        }
    }

    async function onSubmit(values: z.infer<typeof formSchema>) {
        try {
            if (editingId) {
                await RedirectService.update(editingId, values)
                toast.success("Redirect updated")
            } else {
                await RedirectService.create(values)
                toast.success("Redirect created")
            }
            setDialogOpen(false)
            fetchRedirects()
        } catch (error: any) {
            console.error(error)
            if (error.body && error.body.errors) { // Handle API validation errors
                error.body.errors.forEach((err: any) => {
                    form.setError(err.field, { message: err.message })
                })
            } else {
                toast.error("Operation failed")
            }
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Are you sure?")) return
        try {
            await RedirectService.delete(id)
            toast.success("Redirect deleted")
            fetchRedirects()
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete")
        }
    }

    function openCreate() {
        setEditingId(null)
        form.reset({
            source_path: "",
            target_path: "",
            status_code: 301,
            notes: "",
            enabled: true,
        })
        setDialogOpen(true)
    }

    function openEdit(redirect: RedirectResponse) {
        setEditingId(redirect.id)
        form.reset({
            source_path: redirect.source_path,
            target_path: redirect.target_path,
            status_code: redirect.status_code,
            notes: redirect.notes || "",
            enabled: redirect.enabled,
        })
        setDialogOpen(true)
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Redirects</h1>
                    <p className="text-muted-foreground">Manage URL redirects and prevent 404s.</p>
                </div>
                <Button onClick={openCreate} data-testid="redirects-create">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Redirect
                </Button>
            </div>

            {validationIssues.length > 0 && (
                <div className="rounded-md bg-destructive/15 p-4 text-destructive flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 mt-0.5" />
                    <div>
                        <h3 className="font-semibold">Configuration Issues Detected</h3>
                        <ul className="list-disc pl-5 text-sm mt-1">
                            {validationIssues.map((issue, idx) => (
                                <li key={idx}>
                                    {issue.source_path}: {issue.errors.map((e: any) => e.message).join(", ")}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}

            <Card>
                <CardContent className="p-0">
                    <Table data-testid="redirects-table">
                        <TableHeader>
                            <TableRow>
                                <TableHead>Source Path</TableHead>
                                <TableHead>Target Path</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Enabled</TableHead>
                                <TableHead className="w-[100px]"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="h-24 text-center">
                                        <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                                    </TableCell>
                                </TableRow>
                            ) : redirects.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                                        No redirects configured.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                redirects.map((redirect) => (
                                    <TableRow key={redirect.id}>
                                        <TableCell className="font-medium">{redirect.source_path}</TableCell>
                                        <TableCell>{redirect.target_path}</TableCell>
                                        <TableCell>
                                            <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium ring-1 ring-inset ring-gray-500/10">
                                                {redirect.status_code}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            {redirect.enabled ? (
                                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                                            ) : (
                                                <span className="text-muted-foreground text-xs">Disabled</span>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex justify-end gap-2">
                                                <Button variant="ghost" size="icon" onClick={() => openEdit(redirect)}>
                                                    <Pencil className="h-4 w-4" />
                                                </Button>
                                                <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDelete(redirect.id)}>
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{editingId ? "Edit Redirect" : "Add Redirect"}</DialogTitle>
                        <DialogDescription>
                            Configure URL redirection rules.
                        </DialogDescription>
                    </DialogHeader>
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                            <FormField
                                control={form.control}
                                name="source_path"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Source Path</FormLabel>
                                        <FormControl>
                                            <Input placeholder="/old-url" data-testid="redirects-from" {...field} />
                                        </FormControl>
                                        <FormDescription>The path to redirect from.</FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="target_path"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Target Path</FormLabel>
                                        <FormControl>
                                            <Input placeholder="/new-url" data-testid="redirects-to" {...field} />
                                        </FormControl>
                                        <FormDescription>The internal path to redirect to.</FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="status_code"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Status Code</FormLabel>
                                            <FormControl>
                                                <Input type="number" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="enabled"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-col gap-2">
                                            <FormLabel>Enabled</FormLabel>
                                            <FormControl>
                                                <Switch checked={field.value} onCheckedChange={field.onChange} />
                                            </FormControl>
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control}
                                name="notes"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Notes</FormLabel>
                                        <FormControl>
                                            <Input placeholder="Why this redirect exists..." {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <DialogFooter>
                                <Button type="submit">Save Redirect</Button>
                            </DialogFooter>
                        </form>
                    </Form>
                </DialogContent>
            </Dialog>
        </div>
    )
}
