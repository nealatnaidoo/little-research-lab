/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Update an existing PDF resource.
 */
export type ResourcePDFUpdateRequest = {
    title?: (string | null);
    slug?: (string | null);
    summary?: (string | null);
    pdf_asset_id?: (string | null);
    pdf_version_id?: (string | null);
    pinned_policy?: ('pinned' | 'latest' | null);
    display_title?: (string | null);
    download_filename?: (string | null);
};

