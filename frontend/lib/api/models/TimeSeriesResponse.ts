/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TimeSeriesPoint } from './TimeSeriesPoint';
/**
 * Time series response model.
 */
export type TimeSeriesResponse = {
    bucket_type: string;
    points: Array<TimeSeriesPoint>;
};

