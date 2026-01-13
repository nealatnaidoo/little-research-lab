/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ContentBlockModel = {
    id?: (string | null);
    block_type: ContentBlockModel.block_type;
    data_json: Record<string, any>;
    position?: (number | null);
};
export namespace ContentBlockModel {
    export enum block_type {
        MARKDOWN = 'markdown',
        IMAGE = 'image',
        CHART = 'chart',
        EMBED = 'embed',
        DIVIDER = 'divider',
    }
}

