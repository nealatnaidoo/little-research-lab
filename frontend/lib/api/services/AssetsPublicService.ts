/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AssetsPublicService {
    /**
     * Get versioned asset
     * Serve asset by version ID with immutable cache headers (TA-0009, TA-0010).
     * @param assetId
     * @param versionId
     * @param download Trigger download (TA-0011)
     * @returns any Asset content with proper headers
     * @throws ApiError
     */
    public static getVersionedAssetAssetsAssetIdVVersionIdGet(
        assetId: string,
        versionId: string,
        download: boolean = false,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/assets/{asset_id}/v/{version_id}',
            path: {
                'asset_id': assetId,
                'version_id': versionId,
            },
            query: {
                'download': download,
            },
            errors: {
                304: `Not modified (client has cached version)`,
                404: `Version not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get latest asset version
     * Serve latest version of asset (shorter cache).
     * @param assetId
     * @param download Trigger download
     * @returns any Asset content
     * @throws ApiError
     */
    public static getLatestAssetAssetsAssetIdLatestGet(
        assetId: string,
        download: boolean = false,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/assets/{asset_id}/latest',
            path: {
                'asset_id': assetId,
            },
            query: {
                'download': download,
            },
            errors: {
                304: `Not modified`,
                404: `Asset or version not found`,
                422: `Validation Error`,
            },
        });
    }
}
