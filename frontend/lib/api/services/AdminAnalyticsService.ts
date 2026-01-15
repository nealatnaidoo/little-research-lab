/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DashboardResponse } from '../models/DashboardResponse';
import type { EngagementDistributionResponse } from '../models/EngagementDistributionResponse';
import type { EngagementTotalsResponse } from '../models/EngagementTotalsResponse';
import type { TimeSeriesResponse } from '../models/TimeSeriesResponse';
import type { TopContentResponse } from '../models/TopContentResponse';
import type { TopEngagedContentResponse } from '../models/TopEngagedContentResponse';
import type { TopReferrersResponse } from '../models/TopReferrersResponse';
import type { TopSourcesResponse } from '../models/TopSourcesResponse';
import type { TotalsResponse } from '../models/TotalsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminAnalyticsService {
    /**
     * Get Totals
     * Get aggregated totals for a time range (TA-0041).
     *
     * Returns total counts split by real/bot traffic.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param bucketType Bucket type: minute, hour, day
     * @param eventType Filter by event type
     * @param contentId Filter by content ID
     * @param excludeBots Exclude bot traffic
     * @returns TotalsResponse Successful Response
     * @throws ApiError
     */
    public static getTotalsApiAdminAnalyticsTotalsGet(
        start?: (string | null),
        end?: (string | null),
        bucketType: string = 'day',
        eventType?: (string | null),
        contentId?: (string | null),
        excludeBots: boolean = true,
    ): CancelablePromise<TotalsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/totals',
            query: {
                'start': start,
                'end': end,
                'bucket_type': bucketType,
                'event_type': eventType,
                'content_id': contentId,
                'exclude_bots': excludeBots,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Time Series
     * Get time series data for charting (TA-0041).
     *
     * Returns data points with timestamps and counts.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param bucketType Bucket type: minute, hour, day
     * @param eventType Filter by event type
     * @param contentId Filter by content ID
     * @param excludeBots Exclude bot traffic
     * @returns TimeSeriesResponse Successful Response
     * @throws ApiError
     */
    public static getTimeSeriesApiAdminAnalyticsTimeSeriesGet(
        start?: (string | null),
        end?: (string | null),
        bucketType: string = 'hour',
        eventType?: (string | null),
        contentId?: (string | null),
        excludeBots: boolean = true,
    ): CancelablePromise<TimeSeriesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/time-series',
            query: {
                'start': start,
                'end': end,
                'bucket_type': bucketType,
                'event_type': eventType,
                'content_id': contentId,
                'exclude_bots': excludeBots,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Top Content
     * Get top content by views (TA-0042).
     *
     * Returns content IDs sorted by view count.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param bucketType Bucket type: minute, hour, day
     * @param eventType Event type
     * @param limit Number of results
     * @param excludeBots Exclude bot traffic
     * @returns TopContentResponse Successful Response
     * @throws ApiError
     */
    public static getTopContentApiAdminAnalyticsTopContentGet(
        start?: (string | null),
        end?: (string | null),
        bucketType: string = 'day',
        eventType: string = 'page_view',
        limit: number = 10,
        excludeBots: boolean = true,
    ): CancelablePromise<TopContentResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/top-content',
            query: {
                'start': start,
                'end': end,
                'bucket_type': bucketType,
                'event_type': eventType,
                'limit': limit,
                'exclude_bots': excludeBots,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Top Sources
     * Get top traffic sources (TA-0042).
     *
     * Returns UTM sources sorted by view count.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param bucketType Bucket type: minute, hour, day
     * @param limit Number of results
     * @param excludeBots Exclude bot traffic
     * @returns TopSourcesResponse Successful Response
     * @throws ApiError
     */
    public static getTopSourcesApiAdminAnalyticsTopSourcesGet(
        start?: (string | null),
        end?: (string | null),
        bucketType: string = 'day',
        limit: number = 10,
        excludeBots: boolean = true,
    ): CancelablePromise<TopSourcesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/top-sources',
            query: {
                'start': start,
                'end': end,
                'bucket_type': bucketType,
                'limit': limit,
                'exclude_bots': excludeBots,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Top Referrers
     * Get top referrer domains (TA-0042).
     *
     * Returns referrer domains sorted by view count.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param bucketType Bucket type: minute, hour, day
     * @param limit Number of results
     * @param excludeBots Exclude bot traffic
     * @returns TopReferrersResponse Successful Response
     * @throws ApiError
     */
    public static getTopReferrersApiAdminAnalyticsTopReferrersGet(
        start?: (string | null),
        end?: (string | null),
        bucketType: string = 'day',
        limit: number = 10,
        excludeBots: boolean = true,
    ): CancelablePromise<TopReferrersResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/top-referrers',
            query: {
                'start': start,
                'end': end,
                'bucket_type': bucketType,
                'limit': limit,
                'exclude_bots': excludeBots,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Dashboard
     * Get complete dashboard data (TA-0041, TA-0042, E14).
     *
     * Returns totals, time series, top content, sources, referrers, and engagement.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param bucketType Bucket type for time series
     * @returns DashboardResponse Successful Response
     * @throws ApiError
     */
    public static getDashboardApiAdminAnalyticsDashboardGet(
        start?: (string | null),
        end?: (string | null),
        bucketType: string = 'day',
    ): CancelablePromise<DashboardResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/dashboard',
            query: {
                'start': start,
                'end': end,
                'bucket_type': bucketType,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Engagement Totals
     * Get engagement totals for a time range (E14).
     *
     * Returns total and engaged session counts.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param contentId Filter by content ID
     * @returns EngagementTotalsResponse Successful Response
     * @throws ApiError
     */
    public static getEngagementTotalsApiAdminAnalyticsEngagementGet(
        start?: (string | null),
        end?: (string | null),
        contentId?: (string | null),
    ): CancelablePromise<EngagementTotalsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/engagement',
            query: {
                'start': start,
                'end': end,
                'content_id': contentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Engagement Distribution
     * Get engagement distribution by time and scroll buckets (E14).
     *
     * Returns counts per bucket combination.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param contentId Filter by content ID
     * @returns EngagementDistributionResponse Successful Response
     * @throws ApiError
     */
    public static getEngagementDistributionApiAdminAnalyticsEngagementDistributionGet(
        start?: (string | null),
        end?: (string | null),
        contentId?: (string | null),
    ): CancelablePromise<EngagementDistributionResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/engagement/distribution',
            query: {
                'start': start,
                'end': end,
                'content_id': contentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Top Engaged Content
     * Get top content by engaged sessions (E14).
     *
     * Returns content IDs sorted by engaged session count.
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param limit Number of results
     * @returns TopEngagedContentResponse Successful Response
     * @throws ApiError
     */
    public static getTopEngagedContentApiAdminAnalyticsEngagementTopContentGet(
        start?: (string | null),
        end?: (string | null),
        limit: number = 10,
    ): CancelablePromise<TopEngagedContentResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/analytics/engagement/top-content',
            query: {
                'start': start,
                'end': end,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
