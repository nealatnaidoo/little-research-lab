/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ContentTransitionRequest = {
    status: ContentTransitionRequest.status;
    publish_at?: (string | null);
};
export namespace ContentTransitionRequest {
    export enum status {
        DRAFT = 'draft',
        SCHEDULED = 'scheduled',
        PUBLISHED = 'published',
        ARCHIVED = 'archived',
    }
}

