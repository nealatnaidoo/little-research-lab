/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GenerateShareUrlRequest } from '../models/GenerateShareUrlRequest';
import type { GenerateShareUrlResponse } from '../models/GenerateShareUrlResponse';
import type { SharePlatformsResponse } from '../models/SharePlatformsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PublicSharingService {
    /**
     * Generate share URL
     * Generate a platform-specific share URL with UTM tracking parameters.
     * @param requestBody
     * @returns GenerateShareUrlResponse Successful Response
     * @throws ApiError
     */
    public static generateShareUrlEndpointApiPublicShareGeneratePost(
        requestBody: GenerateShareUrlRequest,
    ): CancelablePromise<GenerateShareUrlResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/public/share/generate',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                404: `Content not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get available share platforms
     * Get list of supported sharing platforms.
     * @returns SharePlatformsResponse Successful Response
     * @throws ApiError
     */
    public static getSharePlatformsApiPublicSharePlatformsGet(): CancelablePromise<SharePlatformsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/public/share/platforms',
        });
    }
}
