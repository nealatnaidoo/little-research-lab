/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LinkCreateRequest } from '../models/LinkCreateRequest';
import type { LinkListResponse } from '../models/LinkListResponse';
import type { LinkResponse } from '../models/LinkResponse';
import type { LinkUpdateRequest } from '../models/LinkUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminLinksService {
    /**
     * List Links
     * List all links.
     * @returns LinkListResponse Successful Response
     * @throws ApiError
     */
    public static listLinksApiAdminLinksGet(): CancelablePromise<LinkListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/links',
        });
    }
    /**
     * Create Link
     * Create a new link.
     * @param requestBody
     * @returns LinkResponse Successful Response
     * @throws ApiError
     */
    public static createLinkApiAdminLinksPost(
        requestBody: LinkCreateRequest,
    ): CancelablePromise<LinkResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/links',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Link
     * Get a link by ID.
     * @param linkId
     * @returns LinkResponse Successful Response
     * @throws ApiError
     */
    public static getLinkApiAdminLinksLinkIdGet(
        linkId: string,
    ): CancelablePromise<LinkResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/links/{link_id}',
            path: {
                'link_id': linkId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Link
     * Update a link.
     * @param linkId
     * @param requestBody
     * @returns LinkResponse Successful Response
     * @throws ApiError
     */
    public static updateLinkApiAdminLinksLinkIdPut(
        linkId: string,
        requestBody: LinkUpdateRequest,
    ): CancelablePromise<LinkResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/admin/links/{link_id}',
            path: {
                'link_id': linkId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Link
     * Delete a link.
     * @param linkId
     * @returns void
     * @throws ApiError
     */
    public static deleteLinkApiAdminLinksLinkIdDelete(
        linkId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/admin/links/{link_id}',
            path: {
                'link_id': linkId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
