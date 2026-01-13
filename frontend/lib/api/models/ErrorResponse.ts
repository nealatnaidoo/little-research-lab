/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ValidationErrorResponse } from './ValidationErrorResponse';
/**
 * Error response with validation errors.
 */
export type ErrorResponse = {
    detail: string;
    errors: Array<ValidationErrorResponse>;
};

