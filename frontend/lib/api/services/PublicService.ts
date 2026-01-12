/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentItemResponse } from '../models/ContentItemResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PublicService {
    /**
     * Get Public Home
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPublicHomeApiPublicHomeGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/public/home',
        });
    }
    /**
     * Get Public Content
     * @param slug
     * @returns ContentItemResponse Successful Response
     * @throws ApiError
     */
    public static getPublicContentApiPublicContentSlugGet(
        slug: string,
    ): CancelablePromise<ContentItemResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/public/content/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
