/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Audit entry response model.
 */
export type AuditEntryResponse = {
    id: string;
    timestamp: string;
    action: string;
    entity_type: string;
    entity_id: (string | null);
    actor_id: (string | null);
    actor_name: (string | null);
    description: string;
    metadata: Record<string, any>;
    ip_address: (string | null);
};

