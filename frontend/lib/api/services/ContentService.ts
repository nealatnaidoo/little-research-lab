/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export type ContentItem = {
    id: string;
    title: string;
    slug: string;
    description?: string;
    body?: any;
    status: string;
    publish_at?: string | null;
    scheduled_job_id?: string | null;
};

// Backend block format
type BackendBlock = {
    block_type: string;
    data_json: Record<string, any>;
};

// Convert TipTap JSON to backend blocks format
function bodyToBlocks(body: any): BackendBlock[] {
    if (!body || Object.keys(body).length === 0) {
        return [];
    }
    // Store entire TipTap JSON as a single markdown block
    return [{
        block_type: "markdown",
        data_json: { tiptap: body }
    }];
}

// Convert backend blocks to TipTap JSON
function blocksToBody(blocks: BackendBlock[]): any {
    if (!blocks || blocks.length === 0) {
        return {};
    }
    // Look for tiptap data in first block
    const first = blocks[0];
    if (first?.data_json?.tiptap) {
        return first.data_json.tiptap;
    }
    // Legacy: if there's text, convert to simple doc
    if (first?.data_json?.text) {
        return {
            type: "doc",
            content: [{ type: "paragraph", content: [{ type: "text", text: first.data_json.text }] }]
        };
    }
    return {};
}

// Transform backend response to frontend format
function transformResponse(data: any): ContentItem {
    return {
        id: data.id,
        title: data.title,
        slug: data.slug,
        description: data.summary || "",
        body: blocksToBody(data.blocks || []),
        status: data.status,
        publish_at: data.publish_at,
        scheduled_job_id: null,
    };
}

export class ContentService {

    public static async list(status?: string): Promise<ContentItem[]> {
        const items: any[] = await __request(OpenAPI, {
            method: 'GET',
            url: '/api/content',
            query: { 'status': status },
        });
        return items.map(transformResponse);
    }

    public static async create(data: {
        title: string;
        slug: string;
        description?: string;
        body?: any;
        status?: string;
        type?: string;
    }): Promise<ContentItem> {
        // Convert to backend format
        const backendData = {
            title: data.title,
            slug: data.slug,
            summary: data.description || "",
            type: data.type || "post",
            blocks: bodyToBlocks(data.body),
        };
        const result = await __request(OpenAPI, {
            method: 'POST',
            url: '/api/content',
            body: backendData,
        });
        return transformResponse(result);
    }

    public static async get(id: string): Promise<ContentItem> {
        const result = await __request(OpenAPI, {
            method: 'GET',
            url: `/api/content/${id}`,
        });
        return transformResponse(result);
    }

    public static async update(id: string, data: {
        title?: string;
        slug?: string;
        description?: string;
        body?: any;
        status?: string;
    }): Promise<ContentItem> {
        // Convert to backend format
        const backendData: Record<string, any> = {};
        if (data.title !== undefined) backendData.title = data.title;
        if (data.slug !== undefined) backendData.slug = data.slug;
        if (data.description !== undefined) backendData.summary = data.description;
        if (data.body !== undefined) backendData.blocks = bodyToBlocks(data.body);

        const result = await __request(OpenAPI, {
            method: 'PUT',
            url: `/api/content/${id}`,
            body: backendData,
        });
        return transformResponse(result);
    }

    public static delete(id: string): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: `/api/content/${id}`,
        });
    }

    public static async transition(id: string, data: {
        status: string;
        publish_at?: string;
    }): Promise<ContentItem> {
        const result = await __request(OpenAPI, {
            method: 'POST',
            url: `/api/content/${id}/transition`,
            body: data,
        });
        return transformResponse(result);
    }
}
