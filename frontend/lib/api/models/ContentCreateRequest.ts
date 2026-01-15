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
    tier?: ContentCreateRequest.tier;
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
    export enum tier {
        FREE = 'free',
        PREMIUM = 'premium',
        SUBSCRIBER_ONLY = 'subscriber_only',
    }
    export enum visibility {
        PUBLIC = 'public',
        UNLISTED = 'unlisted',
        PRIVATE = 'private',
    }
    export enum type {
        POST = 'post',
        PAGE = 'page',
        RESOURCE_PDF = 'resource_pdf',
    }
}

