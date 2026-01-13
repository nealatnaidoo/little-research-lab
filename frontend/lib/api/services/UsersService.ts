/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
import type { UserCreateRequest } from '../models/UserCreateRequest';
import type { UserResponse } from '../models/UserResponse';
import type { UserUpdateRequest } from '../models/UserUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UsersService {
    /**
     * List Users
     * @returns UserResponse Successful Response
     * @throws ApiError
     */
    public static listUsersApiUsersGet(): CancelablePromise<Array<UserResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/users',
        });
    }
    /**
     * Create User
     * @param requestBody
     * @returns UserResponse Successful Response
     * @throws ApiError
     */
    public static createUserApiUsersPost(
        requestBody: UserCreateRequest,
    ): CancelablePromise<UserResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/users',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update User
     * @param userId
     * @param requestBody
     * @returns UserResponse Successful Response
     * @throws ApiError
     */
    public static updateUserApiUsersUserIdPut(
        userId: string,
        requestBody: UserUpdateRequest,
    ): CancelablePromise<UserResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/users/{user_id}',
            path: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
