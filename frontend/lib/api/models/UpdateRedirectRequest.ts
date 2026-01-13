/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to update a redirect.
 */
export type UpdateRedirectRequest = {
    /**
     * New source path
     */
    source_path?: (string | null);
    /**
     * New target path
     */
    target_path?: (string | null);
    /**
     * HTTP status code
     */
    status_code?: (number | null);
    /**
     * Enable/disable redirect
     */
    enabled?: (boolean | null);
    /**
     * Admin notes
     */
    notes?: (string | null);
};

