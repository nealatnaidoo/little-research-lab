/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ResourcePDFResponse = {
    id: string;
    title: string;
    slug: string;
    summary: string;
    status: 'draft' | 'scheduled' | 'published' | 'archived';
    owner_user_id: string;
    pdf_asset_id?: string | null;
    pdf_version_id?: string | null;
    pinned_policy: 'pinned' | 'latest';
    display_title?: string | null;
    download_filename?: string | null;
    created_at: string;
    updated_at: string;
    published_at?: string | null;
};
