"use client"

import { useEffect, useState } from "react"
import { format, startOfWeek, endOfWeek, eachDayOfInterval, isSameDay, startOfMonth, endOfMonth, addMonths, subMonths } from "date-fns"
import { Loader2, ChevronLeft, ChevronRight, Calendar as CalendarIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SchedulerService, type CalendarEvent } from "@/lib/api"
import { Badge } from "@/components/ui/badge"

function getEventColor(status: string) {
    switch (status) {
        case "queued": return "bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20"
        case "running": return "bg-blue-500/10 text-blue-500 hover:bg-blue-500/20"
        case "succeeded": return "bg-green-500/10 text-green-500 hover:bg-green-500/20"
        case "failed": return "bg-red-500/10 text-red-500 hover:bg-red-500/20"
        default: return "bg-slate-500/10 text-slate-500 hover:bg-slate-500/20"
    }
}

export default function SchedulePage() {
    const [currentDate, setCurrentDate] = useState(new Date())
    const [events, setEvents] = useState<CalendarEvent[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Calendar View State
    const monthStart = startOfMonth(currentDate)
    const monthEnd = endOfMonth(currentDate)
    const calendarStart = startOfWeek(monthStart)
    const calendarEnd = endOfWeek(monthEnd)

    const days = eachDayOfInterval({
        start: calendarStart,
        end: calendarEnd
    })

    useEffect(() => {
        async function fetchEvents() {
            try {
                setLoading(true)
                setError(null)
                // Fetch events for the visible range
                const response = await SchedulerService.getCalendar(
                    calendarStart.toISOString(),
                    calendarEnd.toISOString()
                )
                setEvents(response.events)
            } catch (err) {
                console.error("Failed to fetch schedule", err)
                setError("Failed to load schedule. Please try again.")
            } finally {
                setLoading(false)
            }
        }

        fetchEvents()
    }, [currentDate]) // Re-fetch when month changes

    const nextMonth = () => setCurrentDate(addMonths(currentDate, 1))
    const prevMonth = () => setCurrentDate(subMonths(currentDate, 1))
    const jumpToday = () => setCurrentDate(new Date())

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Schedule</h1>
                    <p className="text-muted-foreground">Manage scheduled content publishing.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="icon" onClick={prevMonth}>
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <div className="min-w-[140px] text-center font-medium">
                        {format(currentDate, "MMMM yyyy")}
                    </div>
                    <Button variant="outline" size="icon" onClick={nextMonth}>
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" onClick={jumpToday}>
                        Today
                    </Button>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <CalendarIcon className="h-5 w-5" />
                        Monthly View
                    </CardTitle>
                    <CardDescription>All scheduled publishing jobs.</CardDescription>
                </CardHeader>
                <CardContent>
                    {error && (
                        <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                            {error}
                        </div>
                    )}

                    {loading ? (
                        <div className="flex h-96 items-center justify-center">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : (
                        <div className="grid grid-cols-7 gap-px bg-muted text-center text-sm shadow-sm ring-1 ring-inset ring-muted rounded-lg overflow-hidden">
                            {/* Header */}
                            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                                <div key={day} className="bg-background py-2 font-semibold text-muted-foreground">
                                    {day}
                                </div>
                            ))}

                            {/* Days */}
                            {days.map((day, dayIdx) => {
                                const isToday = isSameDay(day, new Date());
                                const isCurrentMonth = day.getMonth() === currentDate.getMonth();
                                const dayEvents = events.filter(e => isSameDay(new Date(e.start), day));

                                return (
                                    <div
                                        key={day.toISOString()}
                                        className={`min-h-[120px] bg-background p-2 ${!isCurrentMonth ? "bg-muted/50 text-muted-foreground" : ""
                                            }`}
                                    >
                                        <div className="flex justify-between items-start">
                                            <span className={`
                                    flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium
                                    ${isToday ? "bg-primary text-primary-foreground" : ""}
                                `}>
                                                {format(day, "d")}
                                            </span>
                                        </div>
                                        <div className="mt-2 space-y-1">
                                            {dayEvents.map(event => (
                                                <Badge
                                                    key={event.id}
                                                    variant="outline"
                                                    className={`w-full justify-start block truncate text-[10px] px-1 py-0.5 border-0 font-normal ${getEventColor(event.status)}`}
                                                    title={`${format(new Date(event.start), "HH:mm")} - ${event.title}`}
                                                >
                                                    <span className="font-semibold">{format(new Date(event.start), "HH:mm")}</span> {event.title}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
