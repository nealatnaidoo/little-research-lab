/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EventRequest } from '../models/EventRequest';
import type { EventResponse } from '../models/EventResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AnalyticsIngestService {
    /**
     * Ingest Event
     * Ingest an analytics event.
     *
     * TA-0034: Validates event type and allowed fields.
     * TA-0035: Rejects forbidden fields (PII).
     *
     * Rate limited: 600 requests per 60 seconds per client.
     * @param requestBody
     * @returns EventResponse Successful Response
     * @throws ApiError
     */
    public static ingestEventAEventPost(
        requestBody: EventRequest,
    ): CancelablePromise<EventResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/a/event',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad Request`,
                422: `Validation Error`,
                429: `Rate limit exceeded`,
            },
        });
    }
    /**
     * Ingest Batch
     * Ingest multiple analytics events.
     *
     * Returns results for each event.
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static ingestBatchABatchPost(
        requestBody: Array<Record<string, any>>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/a/batch',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
