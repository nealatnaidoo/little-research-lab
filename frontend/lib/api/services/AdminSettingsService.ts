/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SettingsResponse } from '../models/SettingsResponse';
import type { SettingsUpdateRequest } from '../models/SettingsUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminSettingsService {
    /**
     * Get site settings
     * Get current site settings. Returns defaults if not configured (TA-0001).
     * @returns SettingsResponse Successful Response
     * @throws ApiError
     */
    public static getSettingsApiAdminSettingsGet(): CancelablePromise<SettingsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/settings',
        });
    }
    /**
     * Update site settings
     * Update site settings with validation (TA-0002).
     * @param requestBody
     * @returns SettingsResponse Successful Response
     * @throws ApiError
     */
    public static updateSettingsApiAdminSettingsPut(
        requestBody: SettingsUpdateRequest,
    ): CancelablePromise<SettingsResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/admin/settings',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation errors with actionable messages`,
                422: `Validation Error`,
            },
        });
    }
}
