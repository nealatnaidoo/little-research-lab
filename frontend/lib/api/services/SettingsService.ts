/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export type SettingsResponse = {
    site_title: string;
    site_subtitle: string;
    avatar_asset_id: string | null;
    theme: string;
    social_links_json: Record<string, string>;
    updated_at: string;
};

export type SettingsFormData = {
    site_title?: string;
    site_subtitle?: string;
    avatar_asset_id?: string | null;
    theme?: string;
    social_links_json?: Record<string, string>;
};

export class SettingsService {

    /**
     * Get Settings
     * @returns SettingsResponse Successful Response
     * @throws ApiError
     */
    public static getSettings(): CancelablePromise<SettingsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/settings',
        });
    }

    /**
     * Update Settings
     * @param requestBody 
     * @returns SettingsResponse Successful Response
     * @throws ApiError
     */
    public static updateSettings(
        requestBody: SettingsFormData,
    ): CancelablePromise<SettingsResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/admin/settings',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
