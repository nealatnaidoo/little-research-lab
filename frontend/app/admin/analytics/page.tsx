"use client"

import { useEffect, useState } from "react"
import { format, subDays } from "date-fns"
import { Loader2, Users, MousePointer, Activity, Globe, Clock, ArrowDownToLine } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { AdminAnalyticsService, OpenAPI, type DashboardResponse } from "@/lib/api"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Engagement API types (not in generated client)
interface EngagementDistributionItem {
    time_bucket: string
    scroll_bucket: string
    count: number
}

interface TopEngagedContentItem {
    content_id: string
    engaged_count: number
}

export default function AnalyticsPage() {
    const [data, setData] = useState<DashboardResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [period, setPeriod] = useState<"7d" | "30d">("7d")
    const [activeTab, setActiveTab] = useState("overview")

    // Engagement tab data
    const [engagementDistribution, setEngagementDistribution] = useState<EngagementDistributionItem[]>([])
    const [topEngagedContent, setTopEngagedContent] = useState<TopEngagedContentItem[]>([])
    const [engagementLoading, setEngagementLoading] = useState(false)

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

    // Fetch engagement-specific data when engagement tab is active
    useEffect(() => {
        if (activeTab !== "engagement") return

        async function fetchEngagementData() {
            try {
                setEngagementLoading(true)
                const end = new Date()
                const start = subDays(end, period === "7d" ? 7 : 30)
                const baseUrl = OpenAPI.BASE || ""

                // Fetch distribution and top content in parallel
                const [distRes, topRes] = await Promise.all([
                    fetch(`${baseUrl}/api/admin/analytics/engagement/distribution?start=${start.toISOString()}&end=${end.toISOString()}`),
                    fetch(`${baseUrl}/api/admin/analytics/engagement/top-content?start=${start.toISOString()}&end=${end.toISOString()}&limit=10`),
                ])

                if (distRes.ok) {
                    const distData = await distRes.json()
                    setEngagementDistribution(distData.items || [])
                }

                if (topRes.ok) {
                    const topData = await topRes.json()
                    setTopEngagedContent(topData.items || [])
                }
            } catch (err) {
                console.error("Failed to fetch engagement data", err)
            } finally {
                setEngagementLoading(false)
            }
        }

        fetchEngagementData()
    }, [activeTab, period])

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

            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="engagement">Engagement</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-6 mt-4">
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
                        {data.engagement ? (
                            <>
                                <div className="text-2xl font-bold">{data.engagement.engaged_sessions.toLocaleString()}</div>
                                <p className="text-xs text-muted-foreground">
                                    {(data.engagement.engagement_rate * 100).toFixed(1)}% engagement rate
                                </p>
                            </>
                        ) : (
                            <>
                                <div className="text-2xl font-bold">0</div>
                                <p className="text-xs text-muted-foreground">No engagement data</p>
                            </>
                        )}
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
                </TabsContent>

                <TabsContent value="engagement" className="space-y-6 mt-4">
                    {engagementLoading ? (
                        <div className="flex h-48 items-center justify-center">
                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : (
                        <>
                            {/* Engagement Summary */}
                            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                                <Card>
                                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                        <CardTitle className="text-sm font-medium">Total Sessions</CardTitle>
                                        <Users className="h-4 w-4 text-muted-foreground" />
                                    </CardHeader>
                                    <CardContent>
                                        <div className="text-2xl font-bold">
                                            {data.engagement?.total_sessions?.toLocaleString() ?? 0}
                                        </div>
                                        <p className="text-xs text-muted-foreground">All tracked sessions</p>
                                    </CardContent>
                                </Card>
                                <Card>
                                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                        <CardTitle className="text-sm font-medium">Engaged Sessions</CardTitle>
                                        <MousePointer className="h-4 w-4 text-muted-foreground" />
                                    </CardHeader>
                                    <CardContent>
                                        <div className="text-2xl font-bold">
                                            {data.engagement?.engaged_sessions?.toLocaleString() ?? 0}
                                        </div>
                                        <p className="text-xs text-muted-foreground">
                                            30s+ time or 50%+ scroll
                                        </p>
                                    </CardContent>
                                </Card>
                                <Card>
                                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                        <CardTitle className="text-sm font-medium">Engagement Rate</CardTitle>
                                        <Activity className="h-4 w-4 text-muted-foreground" />
                                    </CardHeader>
                                    <CardContent>
                                        <div className="text-2xl font-bold">
                                            {((data.engagement?.engagement_rate ?? 0) * 100).toFixed(1)}%
                                        </div>
                                        <p className="text-xs text-muted-foreground">
                                            Of sessions engaged
                                        </p>
                                    </CardContent>
                                </Card>
                                <Card>
                                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                        <CardTitle className="text-sm font-medium">Distribution Points</CardTitle>
                                        <ArrowDownToLine className="h-4 w-4 text-muted-foreground" />
                                    </CardHeader>
                                    <CardContent>
                                        <div className="text-2xl font-bold">{engagementDistribution.length}</div>
                                        <p className="text-xs text-muted-foreground">Unique time/scroll buckets</p>
                                    </CardContent>
                                </Card>
                            </div>

                            {/* Engagement Distribution Heatmap */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Engagement Distribution</CardTitle>
                                    <CardDescription>
                                        Session distribution by time spent and scroll depth
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {engagementDistribution.length > 0 ? (
                                        <EngagementHeatmap data={engagementDistribution} />
                                    ) : (
                                        <div className="text-center py-8 text-muted-foreground">
                                            No engagement distribution data available
                                        </div>
                                    )}
                                </CardContent>
                            </Card>

                            {/* Top Engaged Content */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Top Engaged Content</CardTitle>
                                    <CardDescription>
                                        Content with the most engaged sessions
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {topEngagedContent.length > 0 ? (
                                        <Table>
                                            <TableHeader>
                                                <TableRow>
                                                    <TableHead>Content ID</TableHead>
                                                    <TableHead className="text-right">Engaged Sessions</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {topEngagedContent.map((item) => (
                                                    <TableRow key={item.content_id}>
                                                        <TableCell className="font-medium truncate max-w-[200px]" title={item.content_id}>
                                                            {item.content_id}
                                                        </TableCell>
                                                        <TableCell className="text-right">{item.engaged_count}</TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    ) : (
                                        <div className="text-center py-8 text-muted-foreground">
                                            No top engaged content data available
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    )
}

// Engagement heatmap component
function EngagementHeatmap({ data }: { data: EngagementDistributionItem[] }) {
    // Define bucket order
    const timeBuckets = ["0-10s", "10-30s", "30-60s", "60s+"]
    const scrollBuckets = ["0-25%", "25-50%", "50-75%", "75-100%"]

    // Build lookup map
    const countMap = new Map<string, number>()
    let maxCount = 0
    for (const item of data) {
        const key = `${item.time_bucket}|${item.scroll_bucket}`
        countMap.set(key, item.count)
        if (item.count > maxCount) maxCount = item.count
    }

    // Calculate color intensity
    const getColor = (count: number) => {
        if (count === 0 || maxCount === 0) return "bg-muted"
        const intensity = count / maxCount
        if (intensity > 0.75) return "bg-primary"
        if (intensity > 0.5) return "bg-primary/75"
        if (intensity > 0.25) return "bg-primary/50"
        return "bg-primary/25"
    }

    return (
        <div className="overflow-x-auto">
            <div className="min-w-[400px]">
                {/* Header row */}
                <div className="grid grid-cols-5 gap-1 mb-1">
                    <div className="text-xs text-muted-foreground flex items-end justify-end pr-2 pb-1">
                        <Clock className="h-3 w-3 mr-1" />
                        Time / Scroll
                        <ArrowDownToLine className="h-3 w-3 ml-1" />
                    </div>
                    {scrollBuckets.map((bucket) => (
                        <div key={bucket} className="text-xs font-medium text-center py-1">
                            {bucket}
                        </div>
                    ))}
                </div>

                {/* Data rows */}
                {timeBuckets.map((timeBucket) => (
                    <div key={timeBucket} className="grid grid-cols-5 gap-1 mb-1">
                        <div className="text-xs font-medium flex items-center justify-end pr-2">
                            {timeBucket}
                        </div>
                        {scrollBuckets.map((scrollBucket) => {
                            const count = countMap.get(`${timeBucket}|${scrollBucket}`) ?? 0
                            return (
                                <div
                                    key={scrollBucket}
                                    className={`h-10 rounded flex items-center justify-center text-xs font-medium transition-colors ${getColor(count)} ${count > 0 ? "text-primary-foreground" : "text-muted-foreground"}`}
                                    title={`${timeBucket}, ${scrollBucket}: ${count} sessions`}
                                >
                                    {count > 0 ? count : "-"}
                                </div>
                            )
                        })}
                    </div>
                ))}
            </div>
        </div>
    )
}
