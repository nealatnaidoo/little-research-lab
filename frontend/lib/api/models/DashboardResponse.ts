/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EngagementTotalsResponse } from './EngagementTotalsResponse';
import type { TimeSeriesResponse } from './TimeSeriesResponse';
import type { TopContentResponse } from './TopContentResponse';
import type { TopReferrersResponse } from './TopReferrersResponse';
import type { TopSourcesResponse } from './TopSourcesResponse';
import type { TotalsResponse } from './TotalsResponse';
/**
 * Dashboard summary response.
 */
export type DashboardResponse = {
    period_start: string;
    period_end: string;
    totals: TotalsResponse;
    time_series: TimeSeriesResponse;
    top_content: TopContentResponse;
    top_sources: TopSourcesResponse;
    top_referrers: TopReferrersResponse;
    engagement?: EngagementTotalsResponse | null;
};

