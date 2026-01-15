/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeleteResponse } from '../models/DeleteResponse';
import type { SubscriberListResponse } from '../models/SubscriberListResponse';
import type { SubscriberResponse } from '../models/SubscriberResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminNewsletterService {
    /**
     * List newsletter subscribers
     * List newsletter subscribers with pagination and optional status filter.
     * @param status Filter by status
     * @param offset Pagination offset
     * @param limit Page size
     * @returns SubscriberListResponse Successful Response
     * @throws ApiError
     */
    public static listSubscribersApiAdminNewsletterSubscribersGet(
        status?: ('pending' | 'confirmed' | 'unsubscribed' | null),
        offset?: number,
        limit: number = 50,
    ): CancelablePromise<SubscriberListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/newsletter/subscribers',
            query: {
                'status': status,
                'offset': offset,
                'limit': limit,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get subscriber details
     * Get details of a specific subscriber.
     * @param subscriberId
     * @returns SubscriberResponse Successful Response
     * @throws ApiError
     */
    public static getSubscriberApiAdminNewsletterSubscribersSubscriberIdGet(
        subscriberId: string,
    ): CancelablePromise<SubscriberResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/newsletter/subscribers/{subscriber_id}',
            path: {
                'subscriber_id': subscriberId,
            },
            errors: {
                401: `Unauthorized`,
                404: `Not Found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete subscriber (GDPR)
     * Permanently delete a subscriber and all their data.
     * @param subscriberId
     * @returns DeleteResponse Successful Response
     * @throws ApiError
     */
    public static deleteSubscriberApiAdminNewsletterSubscribersSubscriberIdDelete(
        subscriberId: string,
    ): CancelablePromise<DeleteResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/admin/newsletter/subscribers/{subscriber_id}',
            path: {
                'subscriber_id': subscriberId,
            },
            errors: {
                401: `Unauthorized`,
                404: `Not Found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Export subscribers to CSV
     * Export all subscribers to CSV format for admin reporting.
     * @param status Filter by status
     * @returns any Successful Response
     * @throws ApiError
     */
    public static exportSubscribersCsvApiAdminNewsletterSubscribersExportCsvGet(
        status?: ('pending' | 'confirmed' | 'unsubscribed' | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/newsletter/subscribers/export/csv',
            query: {
                'status': status,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get newsletter stats
     * Get subscriber statistics by status.
     * @returns number Successful Response
     * @throws ApiError
     */
    public static getNewsletterStatsApiAdminNewsletterStatsGet(): CancelablePromise<Record<string, number>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/newsletter/stats',
            errors: {
                401: `Unauthorized`,
            },
        });
    }
}
