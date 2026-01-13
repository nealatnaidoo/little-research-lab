"use client"

import { useState } from "react"
import { Calendar, Clock, Send, X, Loader2, ArchiveRestore } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

interface PublishingControlsProps {
    contentId: string
    currentStatus: string
    publishAt?: string | null
    onPublishNow: () => Promise<void>
    onSchedule: (publishAt: string) => Promise<void>
    onUnschedule: () => Promise<void>
    onUnpublish: () => Promise<void>
    onSaveDraft: () => Promise<void>
    isSaving?: boolean
}

export function PublishingControls({
    contentId,
    currentStatus,
    publishAt,
    onPublishNow,
    onSchedule,
    onUnschedule,
    onUnpublish,
    onSaveDraft,
    isSaving = false,
}: PublishingControlsProps) {
    const [isPublishing, setIsPublishing] = useState(false)
    const [isUnpublishing, setIsUnpublishing] = useState(false)
    const [isScheduling, setIsScheduling] = useState(false)
    const [isUnscheduling, setIsUnscheduling] = useState(false)
    const [scheduleDate, setScheduleDate] = useState("")
    const [showScheduler, setShowScheduler] = useState(false)

    const handlePublishNow = async () => {
        setIsPublishing(true)
        try {
            await onPublishNow()
        } finally {
            setIsPublishing(false)
        }
    }

    const handleSchedule = async () => {
        if (!scheduleDate) {
            // Provide user feedback for empty date
            return
        }
        setIsScheduling(true)
        try {
            // Convert local datetime to UTC ISO string
            const localDate = new Date(scheduleDate)
            const utcString = localDate.toISOString()
            await onSchedule(utcString)
            setShowScheduler(false)
            setScheduleDate("")
        } finally {
            setIsScheduling(false)
        }
    }

    // Get user's timezone for display
    const getUserTimezone = () => {
        try {
            return Intl.DateTimeFormat().resolvedOptions().timeZone
        } catch {
            return "local time"
        }
    }

    const handleUnschedule = async () => {
        setIsUnscheduling(true)
        try {
            await onUnschedule()
        } finally {
            setIsUnscheduling(false)
        }
    }

    const handleUnpublish = async () => {
        setIsUnpublishing(true)
        try {
            await onUnpublish()
        } finally {
            setIsUnpublishing(false)
        }
    }

    // Get minimum datetime (now + 5 minutes)
    const getMinDateTime = () => {
        const now = new Date()
        now.setMinutes(now.getMinutes() + 5)
        return now.toISOString().slice(0, 16)
    }

    const formatScheduledDate = (dateStr: string) => {
        const date = new Date(dateStr)
        return date.toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
        })
    }

    return (
        <Card>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base">Publishing</CardTitle>
                    <StatusBadge status={currentStatus} publishAt={publishAt} />
                </div>
                <CardDescription>
                    {currentStatus === "published"
                        ? "This content is live"
                        : currentStatus === "scheduled"
                        ? `Scheduled for ${publishAt ? formatScheduledDate(publishAt) : "publication"}`
                        : "Save or publish your content"}
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
                {/* Draft actions */}
                {currentStatus === "draft" && (
                    <>
                        <Button
                            className="w-full"
                            onClick={handlePublishNow}
                            disabled={isPublishing || isSaving}
                        >
                            {isPublishing ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="mr-2 h-4 w-4" />
                            )}
                            Publish Now
                        </Button>

                        {!showScheduler ? (
                            <Button
                                variant="outline"
                                className="w-full"
                                onClick={() => setShowScheduler(true)}
                                disabled={isSaving}
                            >
                                <Calendar className="mr-2 h-4 w-4" />
                                Schedule for Later
                            </Button>
                        ) : (
                            <div className="space-y-2 p-3 border rounded-md bg-muted/50">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">Schedule Publication</span>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-6 w-6"
                                        onClick={() => setShowScheduler(false)}
                                    >
                                        <X className="h-4 w-4" />
                                    </Button>
                                </div>
                                <Input
                                    type="datetime-local"
                                    value={scheduleDate}
                                    onChange={(e) => setScheduleDate(e.target.value)}
                                    min={getMinDateTime()}
                                    className="w-full"
                                />
                                <p className="text-xs text-muted-foreground">
                                    Times shown in {getUserTimezone()}
                                </p>
                                <Button
                                    className="w-full"
                                    onClick={handleSchedule}
                                    disabled={!scheduleDate || isScheduling}
                                >
                                    {isScheduling ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <Clock className="mr-2 h-4 w-4" />
                                    )}
                                    Schedule
                                </Button>
                            </div>
                        )}
                    </>
                )}

                {/* Scheduled actions */}
                {currentStatus === "scheduled" && (
                    <>
                        <div className="p-3 border rounded-md bg-muted/50">
                            <div className="flex items-center gap-2 text-sm">
                                <Clock className="h-4 w-4 text-muted-foreground" />
                                <span>
                                    Scheduled for{" "}
                                    <strong>{publishAt ? formatScheduledDate(publishAt) : "publication"}</strong>
                                </span>
                            </div>
                        </div>

                        <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button variant="outline" className="w-full">
                                    <X className="mr-2 h-4 w-4" />
                                    Unschedule
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Unschedule content?</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        This will cancel the scheduled publication and return the content to draft status.
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction onClick={handleUnschedule} disabled={isUnscheduling}>
                                        {isUnscheduling ? "Unscheduling..." : "Unschedule"}
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>

                        <Button
                            className="w-full"
                            onClick={handlePublishNow}
                            disabled={isPublishing}
                        >
                            {isPublishing ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="mr-2 h-4 w-4" />
                            )}
                            Publish Now Instead
                        </Button>
                    </>
                )}

                {/* Published actions */}
                {currentStatus === "published" && (
                    <>
                        <div className="p-3 border rounded-md bg-green-50 dark:bg-[#a8d4a2]/10 text-green-700 dark:text-[#a8d4a2]">
                            <div className="flex items-center gap-2 text-sm">
                                <Send className="h-4 w-4" />
                                <span>This content is published and live</span>
                            </div>
                        </div>

                        <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button variant="outline" className="w-full">
                                    <ArchiveRestore className="mr-2 h-4 w-4" />
                                    Unpublish
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Unpublish content?</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        This will take the content offline and return it to draft status.
                                        You can republish it later.
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction onClick={handleUnpublish} disabled={isUnpublishing}>
                                        {isUnpublishing ? "Unpublishing..." : "Unpublish"}
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    </>
                )}

                {/* Save draft button - always visible for non-published */}
                {currentStatus !== "published" && (
                    <Button
                        variant="secondary"
                        className="w-full"
                        onClick={onSaveDraft}
                        disabled={isSaving}
                    >
                        {isSaving ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : null}
                        Save Draft
                    </Button>
                )}
            </CardContent>
        </Card>
    )
}

function StatusBadge({ status, publishAt }: { status: string; publishAt?: string | null }) {
    switch (status) {
        case "published":
            return <Badge variant="success">Published</Badge>
        case "scheduled":
            return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 dark:bg-[#b4a7d6]/10 dark:text-[#b4a7d6] dark:border-[#b4a7d6]/30">Scheduled</Badge>
        case "draft":
        default:
            return <Badge variant="secondary">Draft</Badge>
    }
}
