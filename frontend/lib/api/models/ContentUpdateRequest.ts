/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentBlockModel } from './ContentBlockModel';
export type ContentUpdateRequest = {
    title?: (string | null);
    slug?: (string | null);
    summary?: (string | null);
    status?: ('draft' | 'scheduled' | 'published' | 'archived' | null);
    visibility?: ('public' | 'unlisted' | 'private' | null);
    publish_at?: (string | null);
    blocks?: (Array<ContentBlockModel> | null);
};

