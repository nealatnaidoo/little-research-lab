/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
import type { LoginRequest } from './LoginRequest';
export type Body_login_for_access_token_api_auth_login_post = {
    json_data?: (LoginRequest | null);
    grant_type?: (string | null);
    username: string;
    password: string;
    scope?: string;
    client_id?: (string | null);
    client_secret?: (string | null);
};

