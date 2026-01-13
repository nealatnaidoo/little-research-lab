/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuditEntryResponse } from '../models/AuditEntryResponse';
import type { AuditQueryResponse } from '../models/AuditQueryResponse';
import type { EntityHistoryResponse } from '../models/EntityHistoryResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminAuditService {
    /**
     * Query Audit Logs
     * Query audit logs with filters (TA-0049).
     *
     * Returns paginated list of audit entries.
     * @param entityType Filter by entity type
     * @param entityId Filter by entity ID
     * @param actorId Filter by actor ID
     * @param action Filter by action
     * @param start Start datetime (ISO format)
     * @param end End datetime (ISO format)
     * @param limit Number of results
     * @param offset Offset for pagination
     * @returns AuditQueryResponse Successful Response
     * @throws ApiError
     */
    public static queryAuditLogsApiAdminAuditGet(
        entityType?: (string | null),
        entityId?: (string | null),
        actorId?: (string | null),
        action?: (string | null),
        start?: (string | null),
        end?: (string | null),
        limit: number = 50,
        offset?: number,
    ): CancelablePromise<AuditQueryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/audit',
            query: {
                'entity_type': entityType,
                'entity_id': entityId,
                'actor_id': actorId,
                'action': action,
                'start': start,
                'end': end,
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Recent Audit Logs
     * Get recent audit logs (TA-0049).
     *
     * Returns entries from the last N hours.
     * @param hours Hours to look back
     * @param limit Number of results
     * @returns AuditQueryResponse Successful Response
     * @throws ApiError
     */
    public static getRecentAuditLogsApiAdminAuditRecentGet(
        hours: number = 24,
        limit: number = 50,
    ): CancelablePromise<AuditQueryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/audit/recent',
            query: {
                'hours': hours,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Entity History
     * Get audit history for a specific entity (TA-0049).
     *
     * Returns all audit entries for the entity.
     * @param entityType
     * @param entityId
     * @returns EntityHistoryResponse Successful Response
     * @throws ApiError
     */
    public static getEntityHistoryApiAdminAuditEntityEntityTypeEntityIdGet(
        entityType: string,
        entityId: string,
    ): CancelablePromise<EntityHistoryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/audit/entity/{entity_type}/{entity_id}',
            path: {
                'entity_type': entityType,
                'entity_id': entityId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Actor Activity
     * Get audit logs for a specific actor (TA-0049).
     *
     * Returns all actions performed by the actor.
     * @param actorId
     * @param limit Number of results
     * @returns AuditQueryResponse Successful Response
     * @throws ApiError
     */
    public static getActorActivityApiAdminAuditActorActorIdGet(
        actorId: string,
        limit: number = 50,
    ): CancelablePromise<AuditQueryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/audit/actor/{actor_id}',
            path: {
                'actor_id': actorId,
            },
            query: {
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Audit Entry
     * Get a specific audit entry by ID (TA-0049).
     *
     * Returns the audit entry or 404 if not found.
     * @param entryId
     * @returns AuditEntryResponse Successful Response
     * @throws ApiError
     */
    public static getAuditEntryApiAdminAuditEntryIdGet(
        entryId: string,
    ): CancelablePromise<AuditEntryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/audit/{entry_id}',
            path: {
                'entry_id': entryId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Audit Summary
     * Get audit log summary statistics (TA-0049).
     *
     * Returns counts by action and entity type.
     * @param hours Hours to look back
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAuditSummaryApiAdminAuditStatsSummaryGet(
        hours: number = 24,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/audit/stats/summary',
            query: {
                'hours': hours,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
