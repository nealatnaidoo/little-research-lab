/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
import type { AssetResponse } from '../models/AssetResponse';

export class AssetService {

    /**
     * Upload File
     * @param file File object
     * @returns AssetResponse Successful Response
     * @throws ApiError
     */
    public static upload(file: File): CancelablePromise<AssetResponse> {
        const formData = new FormData();
        formData.append('file', file);

        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/assets',
            body: formData,
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * List Assets (Basic)
     */
    public static list(limit: number = 20): CancelablePromise<AssetResponse[]> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/assets',
            query: { limit },
        });
    }
}
