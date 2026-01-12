/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AssetResponse = {
    id: string;
    filename_original: string;
    mime_type: string;
    size_bytes: number;
    visibility: AssetResponse.visibility;
    created_at: string;
};
export namespace AssetResponse {
    export enum visibility {
        PUBLIC = 'public',
        UNLISTED = 'unlisted',
        PRIVATE = 'private',
    }
}

