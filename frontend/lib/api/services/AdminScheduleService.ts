/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CalendarResponse } from '../models/CalendarResponse';
import type { JobResponse } from '../models/JobResponse';
import type { PublishNowRequest } from '../models/PublishNowRequest';
import type { PublishNowResponse } from '../models/PublishNowResponse';
import type { RescheduleRequest } from '../models/RescheduleRequest';
import type { ScheduleRequest } from '../models/ScheduleRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminScheduleService {
    /**
     * Schedule Content
     * Schedule content for publishing (TA-0026).
     *
     * Creates a publish job with idempotency check.
     * @param requestBody
     * @returns JobResponse Successful Response
     * @throws ApiError
     */
    public static scheduleContentApiAdminScheduleSchedulePost(
        requestBody: ScheduleRequest,
    ): CancelablePromise<JobResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/schedule/schedule',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Unschedule Content
     * Unschedule (cancel) a publish job (TA-0026).
     *
     * Only queued jobs can be cancelled.
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static unscheduleContentApiAdminScheduleScheduleJobIdDelete(
        jobId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/admin/schedule/schedule/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reschedule Content
     * Reschedule a publish job to a new time.
     *
     * Only queued jobs can be rescheduled.
     * @param jobId
     * @param requestBody
     * @returns JobResponse Successful Response
     * @throws ApiError
     */
    public static rescheduleContentApiAdminScheduleScheduleJobIdPut(
        jobId: string,
        requestBody: RescheduleRequest,
    ): CancelablePromise<JobResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/admin/schedule/schedule/{job_id}',
            path: {
                'job_id': jobId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Job
     * Get a publish job by ID.
     * @param jobId
     * @returns JobResponse Successful Response
     * @throws ApiError
     */
    public static getJobApiAdminScheduleScheduleJobIdGet(
        jobId: string,
    ): CancelablePromise<JobResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/schedule/schedule/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Jobs For Content
     * Get all scheduled jobs for a content item.
     *
     * Returns pending jobs (queued, running, retry_wait).
     * @param contentId
     * @returns JobResponse Successful Response
     * @throws ApiError
     */
    public static getJobsForContentApiAdminScheduleScheduleContentContentIdGet(
        contentId: string,
    ): CancelablePromise<Array<JobResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/schedule/schedule/content/{content_id}',
            path: {
                'content_id': contentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Publish Now
     * Publish content immediately (TA-0033).
     *
     * Creates a job for now and immediately executes it.
     * @param requestBody
     * @returns PublishNowResponse Successful Response
     * @throws ApiError
     */
    public static publishNowApiAdminSchedulePublishNowPost(
        requestBody: PublishNowRequest,
    ): CancelablePromise<PublishNowResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/schedule/publish-now',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Run Due Jobs
     * Manually trigger processing of due jobs.
     *
     * For testing and manual intervention.
     * @param workerId
     * @param maxJobs
     * @returns any Successful Response
     * @throws ApiError
     */
    public static runDueJobsApiAdminScheduleRunDueJobsPost(
        workerId: string = 'api-worker',
        maxJobs: number = 10,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/schedule/run-due-jobs',
            query: {
                'worker_id': workerId,
                'max_jobs': maxJobs,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Calendar
     * Get scheduled jobs for calendar display (TA-0031).
     *
     * Returns jobs within the specified date range formatted for calendar UI.
     *
     * Args:
     * start: Start of date range (UTC)
     * end: End of date range (UTC)
     * status: Optional filter by status (queued, running, completed, failed)
     *
     * Returns:
     * CalendarResponse with events list
     * @param start
     * @param end
     * @param status
     * @returns CalendarResponse Successful Response
     * @throws ApiError
     */
    public static getCalendarApiAdminScheduleCalendarGet(
        start: string,
        end: string,
        status?: (string | null),
    ): CancelablePromise<CalendarResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/schedule/calendar',
            query: {
                'start': start,
                'end': end,
                'status': status,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
