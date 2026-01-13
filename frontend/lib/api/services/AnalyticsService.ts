/* istanbul ignore file */
/* tslint:disable */
 
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export type TotalsResponse = {
    total: number;
    total_with_bots: number;
    real: number;
    bot: number;
    start: string;
    end: string;
};

export type TimeSeriesPoint = {
    timestamp: string;
    count: number;
};

export type TimeSeriesResponse = {
    bucket_type: string;
    points: Array<TimeSeriesPoint>;
};

export type TopContentItem = {
    content_id: string;
    count: number;
};

export type TopContentResponse = {
    items: Array<TopContentItem>;
};

export type TopSourceItem = {
    source: string | null;
    medium: string | null;
    count: number;
};

export type TopSourcesResponse = {
    items: Array<TopSourceItem>;
};

export type TopReferrerItem = {
    domain: string;
    count: number;
};

export type TopReferrersResponse = {
    items: Array<TopReferrerItem>;
};

export type DashboardResponse = {
    period_start: string;
    period_end: string;
    totals: TotalsResponse;
    time_series: TimeSeriesResponse;
    top_content: TopContentResponse;
    top_sources: TopSourcesResponse;
    top_referrers: TopReferrersResponse;
};

export class AnalyticsService {

    /**
     * Get Dashboard
     * @param start Start date string (ISO)
     * @param end End date string (ISO)
     * @param bucketType Bucket type (minute, hour, day)
     * @returns DashboardResponse Successful Response
     * @throws ApiError
     */
    public static getDashboard(
        start?: string,
        end?: string,
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
        });
    }
}
