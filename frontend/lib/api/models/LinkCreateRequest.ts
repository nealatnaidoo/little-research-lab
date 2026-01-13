/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type LinkCreateRequest = {
    slug: string;
    title: string;
    url: string;
    icon?: (string | null);
    status?: LinkCreateRequest.status;
    position?: number;
    visibility?: LinkCreateRequest.visibility;
    group_id?: (string | null);
};
export namespace LinkCreateRequest {
    export enum status {
        ACTIVE = 'active',
        DISABLED = 'disabled',
    }
    export enum visibility {
        PUBLIC = 'public',
        UNLISTED = 'unlisted',
        PRIVATE = 'private',
    }
}

