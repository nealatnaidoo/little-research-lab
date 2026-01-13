/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PublicRedirectsService {
    /**
     * Resolve Redirect Endpoint
     * Resolve a redirect path (Public).
     * Returns {"target": url, "status_code": code} or 404.
     * @param path
     * @returns any Successful Response
     * @throws ApiError
     */
    public static resolveRedirectEndpointApiPublicRedirectsResolveGet(
        path: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/public/redirects/resolve',
            query: {
                'path': path,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
