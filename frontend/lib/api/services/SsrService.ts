/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SsrService {
    /**
     * Homepage SSR
     * Server-side rendered homepage with meta tags (TA-0003, TA-0004).
     * @returns string Successful Response
     * @throws ApiError
     */
    public static ssrHomepageGet(): CancelablePromise<string> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/',
        });
    }
    /**
     * Post SSR
     * Server-side rendered post page with meta tags.
     * @param slug
     * @returns string Successful Response
     * @throws ApiError
     */
    public static ssrPostPSlugGet(
        slug: string,
    ): CancelablePromise<string> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/p/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Static page SSR
     * Server-side rendered static page with meta tags.
     * @param slug
     * @returns string Successful Response
     * @throws ApiError
     */
    public static ssrPagePageSlugGet(
        slug: string,
    ): CancelablePromise<string> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/page/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get SSR metadata
     * Get SSR metadata as JSON (for testing TA-0003, TA-0004).
     * @param path
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getSsrMetadataMetaGet(
        path: string = '/',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/meta',
            query: {
                'path': path,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Resource(PDF) SSR
     * Server-side rendered PDF resource page (E3.2, TA-0016, TA-0017, TA-0018).
     * @param slug
     * @returns string Successful Response
     * @throws ApiError
     */
    public static ssrResourcePdfRSlugGet(
        slug: string,
    ): CancelablePromise<string> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/r/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * XML Sitemap
     * Sitemap for search engines (R2, T-0046). Only published content included.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static sitemapXmlSitemapXmlGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/sitemap.xml',
        });
    }
}
