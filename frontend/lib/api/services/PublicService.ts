/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentItemResponse } from '../models/ContentItemResponse';
import type { PublicSettingsResponse } from '../models/PublicSettingsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PublicService {
    /**
     * Get Public Home
     * Get public home page data: latest posts and links.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPublicHomeApiPublicHomeGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/public/home',
        });
    }
    /**
     * Get Public Content
     * Get published content by slug.
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
    /**
     * Get Public Settings
     * Get public site settings.
     *
     * Returns site configuration that is safe to expose to unauthenticated visitors:
     * - site_title: Display name of the site
     * - site_subtitle: Tagline/description
     * - theme: Default theme preference (light/dark/system)
     * - social_links_json: Social media links for footer
     *
     * Does NOT return sensitive fields like avatar_asset_id or internal configuration.
     * @returns PublicSettingsResponse Successful Response
     * @throws ApiError
     */
    public static getPublicSettingsApiPublicSettingsGet(): CancelablePromise<PublicSettingsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/public/settings',
        });
    }
}
