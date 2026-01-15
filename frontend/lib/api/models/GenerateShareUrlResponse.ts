/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response containing the generated share URL.
 */
export type GenerateShareUrlResponse = {
    /**
     * Platform-specific share URL with UTM params
     */
    share_url: string;
    /**
     * Target platform
     */
    platform: string;
    /**
     * UTM source value
     */
    utm_source: string;
    /**
     * UTM medium value
     */
    utm_medium: string;
    /**
     * UTM campaign value (content slug)
     */
    utm_campaign: string;
};

