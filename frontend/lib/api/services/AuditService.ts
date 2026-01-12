/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export type AuditEntryResponse = {
    id: string;
    timestamp: string;
    action: string;
    entity_type: string;
    entity_id: string | null;
    actor_id: string | null;
    actor_name: string | null;
    description: string;
    metadata: Record<string, any>;
    ip_address: string | null;
};

export type AuditQueryResponse = {
    items: AuditEntryResponse[];
    total: number;
    offset: number;
    limit: number;
};

export class AuditService {

    public static query(params: {
        entity_type?: string;
        entity_id?: string;
        actor_id?: string;
        action?: string;
        start?: string; // ISO
        end?: string; // ISO
        limit?: number;
        offset?: number;
    }): CancelablePromise<AuditQueryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/audit',
            query: params,
        });
    }

    public static getRecent(hours: number = 24, limit: number = 50): CancelablePromise<AuditQueryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/audit/recent',
            query: { hours, limit },
        });
    }

    public static getEntityHistory(entityType: string, entityId: string): CancelablePromise<{ entries: AuditEntryResponse[] }> {
        return __request(OpenAPI, {
            method: 'GET',
            url: `/api/admin/audit/entity/${entityType}/${entityId}`,
        });
    }
}
