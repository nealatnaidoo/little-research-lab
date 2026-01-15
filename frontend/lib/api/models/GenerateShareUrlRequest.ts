/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for share URL generation.
 */
export type GenerateShareUrlRequest = {
    /**
     * ID of the content to share
     */
    content_id: string;
    /**
     * Target sharing platform
     */
    platform: GenerateShareUrlRequest.platform;
};
export namespace GenerateShareUrlRequest {
    /**
     * Target sharing platform
     */
    export enum platform {
        TWITTER = 'twitter',
        LINKEDIN = 'linkedin',
        FACEBOOK = 'facebook',
        NATIVE = 'native',
    }
}

