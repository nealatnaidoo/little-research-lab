/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentBlockModel } from './ContentBlockModel';
export type ContentItemResponse = {
    title: string;
    slug: string;
    summary?: (string | null);
    status?: ContentItemResponse.status;
    tier?: ContentItemResponse.tier;
    visibility?: ContentItemResponse.visibility;
    publish_at?: (string | null);
    id: string;
    type: ContentItemResponse.type;
    published_at?: (string | null);
    owner_user_id: string;
    created_at: string;
    updated_at: string;
    blocks?: Array<ContentBlockModel>;
};
export namespace ContentItemResponse {
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

