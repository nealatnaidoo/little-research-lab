/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AssetResponse } from '../models/AssetResponse';
import type { Body_upload_asset_api_assets_post } from '../models/Body_upload_asset_api_assets_post';
import type { SetLatestRequest } from '../models/SetLatestRequest';
import type { SetLatestResponse } from '../models/SetLatestResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AssetsService {
    /**
     * List Assets
     * List all assets.
     * @returns AssetResponse Successful Response
     * @throws ApiError
     */
    public static listAssetsApiAssetsGet(): CancelablePromise<Array<AssetResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/assets',
        });
    }
    /**
     * Upload Asset
     * Upload a new asset.
     * @param formData
     * @returns AssetResponse Successful Response
     * @throws ApiError
     */
    public static uploadAssetApiAssetsPost(
        formData: Body_upload_asset_api_assets_post,
    ): CancelablePromise<AssetResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/assets',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Asset Content
     * Get asset file content.
     * @param assetId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAssetContentApiAssetsAssetIdContentGet(
        assetId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/assets/{asset_id}/content',
            path: {
                'asset_id': assetId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Set Latest Version
     * Set a specific version as the latest for an asset.
     *
     * Spec refs: E2.3, TA-0012, TA-0013
     *
     * This allows admins to rollback the /latest pointer to a previous version,
     * ensuring stable versioned URLs while enabling flexibility in what /latest serves.
     * @param assetId
     * @param requestBody
     * @returns SetLatestResponse Successful Response
     * @throws ApiError
     */
    public static setLatestVersionApiAssetsAssetIdSetLatestPost(
        assetId: string,
        requestBody: SetLatestRequest,
    ): CancelablePromise<SetLatestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/assets/{asset_id}/set_latest',
            path: {
                'asset_id': assetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
