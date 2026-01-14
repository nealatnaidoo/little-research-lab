/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ResourcePDFCreateRequest = {
    title: string;
    slug: string;
    summary?: string | null;
    pdf_asset_id?: string | null;
    pdf_version_id?: string | null;
    pinned_policy?: 'pinned' | 'latest';
    display_title?: string | null;
    download_filename?: string | null;
};
