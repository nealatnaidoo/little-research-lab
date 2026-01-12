/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentBlockModel } from './ContentBlockModel';
export type ContentCreateRequest = {
    title: string;
    slug: string;
    summary?: (string | null);
    status?: ContentCreateRequest.status;
    visibility?: ContentCreateRequest.visibility;
    publish_at?: (string | null);
    type: ContentCreateRequest.type;
    blocks?: Array<ContentBlockModel>;
};
export namespace ContentCreateRequest {
    export enum status {
        DRAFT = 'draft',
        SCHEDULED = 'scheduled',
        PUBLISHED = 'published',
        ARCHIVED = 'archived',
    }
    export enum visibility {
        PUBLIC = 'public',
        UNLISTED = 'unlisted',
        PRIVATE = 'private',
    }
    export enum type {
        POST = 'post',
        PAGE = 'page',
    }
}

