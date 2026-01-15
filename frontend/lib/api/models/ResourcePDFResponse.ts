/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * PDF resource response.
 */
export type ResourcePDFResponse = {
    id: string;
    title: string;
    slug: string;
    summary: string;
    status: ResourcePDFResponse.status;
    owner_user_id: string;
    pdf_asset_id?: (string | null);
    pdf_version_id?: (string | null);
    pinned_policy: ResourcePDFResponse.pinned_policy;
    display_title?: (string | null);
    download_filename?: (string | null);
    created_at: string;
    updated_at: string;
    published_at?: (string | null);
};
export namespace ResourcePDFResponse {
    export enum status {
        DRAFT = 'draft',
        SCHEDULED = 'scheduled',
        PUBLISHED = 'published',
        ARCHIVED = 'archived',
    }
    export enum pinned_policy {
        PINNED = 'pinned',
        LATEST = 'latest',
    }
}

