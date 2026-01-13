/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Publish job response.
 */
export type JobResponse = {
    id: string;
    content_id: string;
    publish_at_utc: string;
    status: string;
    attempts: number;
    created_at: string;
    updated_at: string;
    next_retry_at?: (string | null);
    completed_at?: (string | null);
    actual_publish_at?: (string | null);
    error_message?: (string | null);
};

