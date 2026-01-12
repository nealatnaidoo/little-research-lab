/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export type CalendarEvent = {
    id: string;
    content_id: string;
    title: string;
    start: string;
    status: string;
    is_all_day: boolean;
};

export type CalendarResponse = {
    events: Array<CalendarEvent>;
    start_date: string;
    end_date: string;
    total_count: number;
};

export type ScheduleJobResponse = {
    id: string;
    content_id: string;
    publish_at_utc: string;
    status: string;
    created_at: string;
};

export class SchedulerService {

    /**
     * Get Calendar Events
     */
    public static getCalendar(
        start: string,
        end: string,
        status?: string,
    ): CancelablePromise<CalendarResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/schedule/calendar',
            query: {
                'start': start,
                'end': end,
                'status': status,
            },
        });
    }

    /**
     * Publish content immediately
     */
    public static publishNow(contentId: string): CancelablePromise<{ message: string }> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/schedule/publish-now',
            body: { content_id: contentId },
        });
    }

    /**
     * Schedule content for future publication
     */
    public static schedule(
        contentId: string,
        publishAtUtc: string,
    ): CancelablePromise<ScheduleJobResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/schedule/schedule',
            body: {
                content_id: contentId,
                publish_at_utc: publishAtUtc,
            },
        });
    }

    /**
     * Get scheduled jobs for a content item
     */
    public static getJobsForContent(contentId: string): CancelablePromise<ScheduleJobResponse[]> {
        return __request(OpenAPI, {
            method: 'GET',
            url: `/api/admin/schedule/schedule/content/${contentId}`,
        });
    }

    /**
     * Cancel a scheduled job (unschedule)
     */
    public static unschedule(jobId: string): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: `/api/admin/schedule/schedule/${jobId}`,
        });
    }

    /**
     * Reschedule a job to a new time
     */
    public static reschedule(
        jobId: string,
        publishAtUtc: string,
    ): CancelablePromise<ScheduleJobResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: `/api/admin/schedule/schedule/${jobId}`,
            body: { publish_at_utc: publishAtUtc },
        });
    }
}
