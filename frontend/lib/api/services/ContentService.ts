/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentCreateRequest } from '../models/ContentCreateRequest';
import type { ContentItemResponse } from '../models/ContentItemResponse';
import type { ContentTransitionRequest } from '../models/ContentTransitionRequest';
import type { ContentUpdateRequest } from '../models/ContentUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ContentService {
    /**
     * List Content
     * List all content items for admin.
     * @param status
     * @returns ContentItemResponse Successful Response
     * @throws ApiError
     */
    public static listContentApiContentGet(
        status?: (string | null),
    ): CancelablePromise<Array<ContentItemResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/content',
            query: {
                'status': status,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Content
     * Create a new content item.
     * @param requestBody
     * @returns ContentItemResponse Successful Response
     * @throws ApiError
     */
    public static createContentApiContentPost(
        requestBody: ContentCreateRequest,
    ): CancelablePromise<ContentItemResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/content',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Content
     * Get a specific content item.
     * @param itemId
     * @returns ContentItemResponse Successful Response
     * @throws ApiError
     */
    public static getContentApiContentItemIdGet(
        itemId: string,
    ): CancelablePromise<ContentItemResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/content/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Content
     * Update an existing content item.
     * @param itemId
     * @param requestBody
     * @returns ContentItemResponse Successful Response
     * @throws ApiError
     */
    public static updateContentApiContentItemIdPut(
        itemId: string,
        requestBody: ContentUpdateRequest,
    ): CancelablePromise<ContentItemResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/content/{item_id}',
            path: {
                'item_id': itemId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Content
     * Delete a content item.
     * @param itemId
     * @returns void
     * @throws ApiError
     */
    public static deleteContentApiContentItemIdDelete(
        itemId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/content/{item_id}',
            path: {
                'item_id': itemId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Transition Content
     * Transition content status.
     * @param itemId
     * @param requestBody
     * @returns ContentItemResponse Successful Response
     * @throws ApiError
     */
    public static transitionContentApiContentItemIdTransitionPost(
        itemId: string,
        requestBody: ContentTransitionRequest,
    ): CancelablePromise<ContentItemResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/content/{item_id}/transition',
            path: {
                'item_id': itemId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
