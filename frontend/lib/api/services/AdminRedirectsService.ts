/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreateRedirectRequest } from '../models/CreateRedirectRequest';
import type { RedirectListResponse } from '../models/RedirectListResponse';
import type { RedirectResponse } from '../models/RedirectResponse';
import type { UpdateRedirectRequest } from '../models/UpdateRedirectRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminRedirectsService {
    /**
     * List Redirects
     * List all redirects.
     * @returns RedirectListResponse Successful Response
     * @throws ApiError
     */
    public static listRedirectsApiAdminRedirectsRedirectsGet(): CancelablePromise<RedirectListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/redirects/redirects',
        });
    }
    /**
     * Create Redirect
     * Create a new redirect.
     *
     * Validates:
     * - TA-0043: No loops
     * - TA-0044: Internal targets only
     * - TA-0045: Chain length <= 3
     * @param requestBody
     * @returns RedirectResponse Successful Response
     * @throws ApiError
     */
    public static createRedirectApiAdminRedirectsRedirectsPost(
        requestBody: CreateRedirectRequest,
    ): CancelablePromise<RedirectResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/redirects/redirects',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad Request`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Redirect
     * Get a redirect by ID.
     * @param redirectId
     * @returns RedirectResponse Successful Response
     * @throws ApiError
     */
    public static getRedirectApiAdminRedirectsRedirectsRedirectIdGet(
        redirectId: string,
    ): CancelablePromise<RedirectResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/redirects/redirects/{redirect_id}',
            path: {
                'redirect_id': redirectId,
            },
            errors: {
                404: `Redirect not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Redirect
     * Update a redirect.
     *
     * Validates same constraints as create.
     * @param redirectId
     * @param requestBody
     * @returns RedirectResponse Successful Response
     * @throws ApiError
     */
    public static updateRedirectApiAdminRedirectsRedirectsRedirectIdPut(
        redirectId: string,
        requestBody: UpdateRedirectRequest,
    ): CancelablePromise<RedirectResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/admin/redirects/redirects/{redirect_id}',
            path: {
                'redirect_id': redirectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad Request`,
                404: `Redirect not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Redirect
     * Delete a redirect.
     * @param redirectId
     * @returns boolean Successful Response
     * @throws ApiError
     */
    public static deleteRedirectApiAdminRedirectsRedirectsRedirectIdDelete(
        redirectId: string,
    ): CancelablePromise<Record<string, boolean>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/admin/redirects/redirects/{redirect_id}',
            path: {
                'redirect_id': redirectId,
            },
            errors: {
                404: `Redirect not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Resolve Redirect
     * Resolve a redirect path.
     *
     * Returns the final target and status code after following chains.
     * @param path
     * @returns any Successful Response
     * @throws ApiError
     */
    public static resolveRedirectApiAdminRedirectsRedirectsResolvePathGet(
        path: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/redirects/redirects/resolve/{path}',
            path: {
                'path': path,
            },
            errors: {
                404: `No redirect for this path`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Validate Redirects
     * Validate all existing redirects.
     *
     * Returns any redirects with validation issues.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static validateRedirectsApiAdminRedirectsRedirectsValidatePost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/redirects/redirects/validate',
        });
    }
}
