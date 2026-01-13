/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuditEntryResponse } from './AuditEntryResponse';
/**
 * Paginated audit query response.
 */
export type AuditQueryResponse = {
    items: Array<AuditEntryResponse>;
    total: number;
    offset: number;
    limit: number;
};

