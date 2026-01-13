"use client"

import { useEffect, useState } from "react"
import { format, subDays } from "date-fns"
import { Loader2, Users, MousePointer, Activity, Globe } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { AdminAnalyticsService, type DashboardResponse } from "@/lib/api"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export default function AnalyticsPage() {
    const [data, setData] = useState<DashboardResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [period, setPeriod] = useState<"7d" | "30d">("7d")

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true)
                setError(null)

                const end = new Date()
                const start = subDays(end, period === "7d" ? 7 : 30)

                const response = await AdminAnalyticsService.getDashboardApiAdminAnalyticsDashboardGet(
                    start.toISOString(),
                    end.toISOString(),
                    "day"
                )
                setData(response)
            } catch (err) {
                console.error("Failed to fetch analytics", err)
                setError("Failed to load analytics. Please try again.")
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [period])

    if (loading) {
        return (
            <div className="flex h-96 items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (error || !data) {
        return (
            <div className="rounded-md bg-destructive/10 p-4 text-destructive">
                {error || "No data available"}
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
                    <p className="text-muted-foreground">Traffic statistics and source insights.</p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant={period === "7d" ? "default" : "outline"}
                        onClick={() => setPeriod("7d")}
                        size="sm"
                    >
                        Last 7 Days
                    </Button>
                    <Button
                        variant={period === "30d" ? "default" : "outline"}
                        onClick={() => setPeriod("30d")}
                        size="sm"
                    >
                        Last 30 Days
                    </Button>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Views</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{data.totals.total.toLocaleString()}</div>
                        <p className="text-xs text-muted-foreground">Raw requests</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Real Users</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{data.totals.real.toLocaleString()}</div>
                        <p className="text-xs text-muted-foreground">
                            {((data.totals.real / (data.totals.total || 1)) * 100).toFixed(1)}% of total
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Bot Traffic</CardTitle>
                        <Globe className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{data.totals.bot.toLocaleString()}</div>
                        <p className="text-xs text-muted-foreground">Crawlers & bots</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Engaged Sessions</CardTitle>
                        <MousePointer className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {/* Placeholder for future engagement metric */}
                        <div className="text-2xl font-bold">-</div>
                        <p className="text-xs text-muted-foreground">Coming soon</p>
                    </CardContent>
                </Card>
            </div>

            {/* Chart */}
            <Card>
                <CardHeader>
                    <CardTitle>Traffic Overview</CardTitle>
                    <CardDescription>Daily page views over time.</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data.time_series.points}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis
                                    dataKey="timestamp"
                                    tickFormatter={(str) => format(new Date(str), "MMM d")}
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <YAxis
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    tickFormatter={(value) => `${value}`}
                                />
                                <Tooltip
                                    labelFormatter={(label) => format(new Date(label), "MMM d, yyyy")}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="count"
                                    stroke="#8884d8"
                                    strokeWidth={2}
                                    dot={false}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* Top Content */}
                <Card className="col-span-1">
                    <CardHeader>
                        <CardTitle>Top Content</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Content ID</TableHead>
                                    <TableHead className="text-right">Views</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {data.top_content.items.map((item) => (
                                    <TableRow key={item.content_id}>
                                        <TableCell className="font-medium truncate max-w-[150px]" title={item.content_id}>
                                            {item.content_id}
                                        </TableCell>
                                        <TableCell className="text-right">{item.count}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                {/* Top Sources */}
                <Card className="col-span-1">
                    <CardHeader>
                        <CardTitle>Top Sources</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Source / Medium</TableHead>
                                    <TableHead className="text-right">Views</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {data.top_sources.items.map((item, idx) => (
                                    <TableRow key={idx}>
                                        <TableCell>
                                            <div className="font-medium">{item.source || "Direct"}</div>
                                            <div className="text-xs text-muted-foreground">{item.medium || "-"}</div>
                                        </TableCell>
                                        <TableCell className="text-right">{item.count}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                {/* Top Referrers */}
                <Card className="col-span-1">
                    <CardHeader>
                        <CardTitle>Top Referrers</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Domain</TableHead>
                                    <TableHead className="text-right">Views</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {data.top_referrers.items.map((item, idx) => (
                                    <TableRow key={idx}>
                                        <TableCell className="font-medium">{item.domain}</TableCell>
                                        <TableCell className="text-right">{item.count}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
