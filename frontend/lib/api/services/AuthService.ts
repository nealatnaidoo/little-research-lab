/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_login_for_access_token_api_auth_login_post } from '../models/Body_login_for_access_token_api_auth_login_post';
import type { Token } from '../models/Token';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
    /**
     * Login For Access Token
     * Authenticate user and return access token.
     * @param formData
     * @returns Token Successful Response
     * @throws ApiError
     */
    public static loginForAccessTokenApiAuthLoginPost(
        formData: Body_login_for_access_token_api_auth_login_post,
    ): CancelablePromise<Token> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/login',
            formData: formData,
            mediaType: 'application/x-www-form-urlencoded',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Logout
     * Log out user by clearing cookie.
     * @returns string Successful Response
     * @throws ApiError
     */
    public static logoutApiAuthLogoutPost(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/logout',
        });
    }
    /**
     * Read Users Me
     * Get current user info.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readUsersMeApiAuthMeGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/me',
        });
    }
    /**
     * Dev Force Login
     * Dev-only: Auto-login as admin for testing.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static devForceLoginApiAuthDevLoginGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/dev/login',
        });
    }
}
