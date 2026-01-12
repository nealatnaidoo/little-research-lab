/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export type RedirectResponse = {
    id: string;
    source_path: string;
    target_path: string;
    status_code: number;
    enabled: boolean;
    created_at: string;
    updated_at: string;
    notes?: string | null;
};

export type RedirectListResponse = {
    redirects: RedirectResponse[];
    count: number;
};

export type CreateRedirectRequest = {
    source_path: string;
    target_path: string;
    status_code?: number;
    notes?: string;
};

export type UpdateRedirectRequest = {
    source_path?: string;
    target_path?: string;
    status_code?: number;
    enabled?: boolean;
    notes?: string;
};

export type ValidationErrorResponse = {
    errors: Array<{
        code: string;
        message: string;
        field?: string;
    }>;
};

export class RedirectService {

    public static list(): CancelablePromise<RedirectListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/redirects/redirects', // Note: Route path is /redirects in the router, which is prefixed with /api/admin/redirects in main.py. Wait.
            // In main.py: prefix="/api/admin/redirects"
            // In router: @router.post("/redirects") -> /api/admin/redirects/redirects
            // This double nesting seems redundant. Let me check main.py again.
            // main.py: app.include_router(admin_redirects.router, prefix="/api/admin/redirects")
            // admin_redirects.py: @router.get("/redirects")
            // Result: /api/admin/redirects/redirects
            // This is slightly awkward naming but I must follow the code.
        });
    }

    public static create(data: CreateRedirectRequest): CancelablePromise<RedirectResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/redirects/redirects',
            body: data,
            errors: {
                400: `Validation Error`,
            },
        });
    }

    public static get(id: string): CancelablePromise<RedirectResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: `/api/admin/redirects/redirects/${id}`,
            errors: {
                404: `Not Found`,
            },
        });
    }

    public static update(id: string, data: UpdateRedirectRequest): CancelablePromise<RedirectResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: `/api/admin/redirects/redirects/${id}`,
            body: data,
            errors: {
                400: `Validation Error`,
                404: `Not Found`,
            },
        });
    }

    public static delete(id: string): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: `/api/admin/redirects/redirects/${id}`,
            errors: {
                404: `Not Found`,
            },
        });
    }

    public static validate(): CancelablePromise<{ valid: boolean, issues: any[], total_checked: number }> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/redirects/redirects/validate',
        });
    }
}
