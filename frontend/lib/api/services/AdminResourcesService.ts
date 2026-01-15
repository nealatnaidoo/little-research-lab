/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResourcePDFCreateRequest } from '../models/ResourcePDFCreateRequest';
import type { ResourcePDFResponse } from '../models/ResourcePDFResponse';
import type { ResourcePDFUpdateRequest } from '../models/ResourcePDFUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminResourcesService {
    /**
     * List Resources
     * List all PDF resources.
     * @returns ResourcePDFResponse Successful Response
     * @throws ApiError
     */
    public static listResourcesApiAdminResourcesGet(): CancelablePromise<Array<ResourcePDFResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/resources',
        });
    }
    /**
     * Create Resource
     * Create a new PDF resource draft (TA-0014).
     * @param requestBody
     * @returns ResourcePDFResponse Successful Response
     * @throws ApiError
     */
    public static createResourceApiAdminResourcesPost(
        requestBody: ResourcePDFCreateRequest,
    ): CancelablePromise<ResourcePDFResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/resources',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Resource
     * Get a specific PDF resource.
     * @param resourceId
     * @returns ResourcePDFResponse Successful Response
     * @throws ApiError
     */
    public static getResourceApiAdminResourcesResourceIdGet(
        resourceId: string,
    ): CancelablePromise<ResourcePDFResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/resources/{resource_id}',
            path: {
                'resource_id': resourceId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Resource
     * Update an existing PDF resource.
     * @param resourceId
     * @param requestBody
     * @returns ResourcePDFResponse Successful Response
     * @throws ApiError
     */
    public static updateResourceApiAdminResourcesResourceIdPut(
        resourceId: string,
        requestBody: ResourcePDFUpdateRequest,
    ): CancelablePromise<ResourcePDFResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/admin/resources/{resource_id}',
            path: {
                'resource_id': resourceId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Resource
     * Delete a PDF resource.
     * @param resourceId
     * @returns void
     * @throws ApiError
     */
    public static deleteResourceApiAdminResourcesResourceIdDelete(
        resourceId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/admin/resources/{resource_id}',
            path: {
                'resource_id': resourceId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Set Pinned Policy
     * Set pinned policy for a resource (TA-0015).
     * @param resourceId
     * @param policyType
     * @param versionId
     * @returns ResourcePDFResponse Successful Response
     * @throws ApiError
     */
    public static setPinnedPolicyApiAdminResourcesResourceIdPinnedPolicyPost(
        resourceId: string,
        policyType: string,
        versionId?: (string | null),
    ): CancelablePromise<ResourcePDFResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/resources/{resource_id}/pinned-policy',
            path: {
                'resource_id': resourceId,
            },
            query: {
                'policy_type': policyType,
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
