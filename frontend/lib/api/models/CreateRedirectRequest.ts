/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to create a redirect.
 */
export type CreateRedirectRequest = {
    /**
     * Source path (e.g., /old-page)
     */
    source_path: string;
    /**
     * Target path (e.g., /new-page)
     */
    target_path: string;
    /**
     * HTTP status code (301/302)
     */
    status_code?: (number | null);
    /**
     * Admin notes
     */
    notes?: (string | null);
};

