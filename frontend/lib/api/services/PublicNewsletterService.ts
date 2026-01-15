/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConfirmResponse } from '../models/ConfirmResponse';
import type { SubscribeRequest } from '../models/SubscribeRequest';
import type { SubscribeResponse } from '../models/SubscribeResponse';
import type { UnsubscribeResponse } from '../models/UnsubscribeResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PublicNewsletterService {
    /**
     * Subscribe to newsletter
     * Start the double opt-in subscription flow. Sends confirmation email.
     * @param requestBody
     * @returns SubscribeResponse Successful Response
     * @throws ApiError
     */
    public static subscribeToNewsletterApiPublicNewsletterSubscribePost(
        requestBody: SubscribeRequest,
    ): CancelablePromise<SubscribeResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/public/newsletter/subscribe',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                422: `Validation Error`,
                429: `Rate limit exceeded`,
            },
        });
    }
    /**
     * Confirm newsletter subscription
     * Confirm subscription via token from confirmation email.
     * @param token
     * @returns ConfirmResponse Successful Response
     * @throws ApiError
     */
    public static confirmSubscriptionApiPublicNewsletterConfirmGet(
        token: string,
    ): CancelablePromise<ConfirmResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/public/newsletter/confirm',
            query: {
                'token': token,
            },
            errors: {
                400: `Invalid or expired token`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Unsubscribe from newsletter
     * Unsubscribe via token from newsletter emails.
     * @param token
     * @returns UnsubscribeResponse Successful Response
     * @throws ApiError
     */
    public static unsubscribeFromNewsletterApiPublicNewsletterUnsubscribeGet(
        token: string,
    ): CancelablePromise<UnsubscribeResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/public/newsletter/unsubscribe',
            query: {
                'token': token,
            },
            errors: {
                400: `Invalid token`,
                422: `Validation Error`,
            },
        });
    }
}
