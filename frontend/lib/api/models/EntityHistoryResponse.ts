/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuditEntryResponse } from './AuditEntryResponse';
/**
 * Entity history response.
 */
export type EntityHistoryResponse = {
    entity_type: string;
    entity_id: string;
    entries: Array<AuditEntryResponse>;
};

