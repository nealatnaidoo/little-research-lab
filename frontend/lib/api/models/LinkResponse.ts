/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type LinkResponse = {
    id: string;
    slug: string;
    title: string;
    url: string;
    icon: (string | null);
    status: LinkResponse.status;
    position: number;
    visibility: LinkResponse.visibility;
    group_id: (string | null);
};
export namespace LinkResponse {
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

