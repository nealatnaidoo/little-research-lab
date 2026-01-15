/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SubscriberResponse } from './SubscriberResponse';
/**
 * Paginated list of subscribers.
 */
export type SubscriberListResponse = {
    subscribers: Array<SubscriberResponse>;
    /**
     * Total matching subscribers
     */
    total: number;
    /**
     * Current offset
     */
    offset: number;
    /**
     * Page size
     */
    limit: number;
};

