/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CalendarEvent } from './CalendarEvent';
/**
 * Calendar API response (TA-0031).
 */
export type CalendarResponse = {
    events: Array<CalendarEvent>;
    start_date: string;
    end_date: string;
    total_count: number;
};

