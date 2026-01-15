/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Newsletter subscriber response (tokens hidden for security).
 */
export type SubscriberResponse = {
    /**
     * Subscriber ID
     */
    id: string;
    /**
     * Email address
     */
    email: string;
    /**
     * Subscription status
     */
    status: string;
    /**
     * Creation timestamp
     */
    created_at: string;
    /**
     * Confirmation timestamp
     */
    confirmed_at?: (string | null);
    /**
     * Unsubscribe timestamp
     */
    unsubscribed_at?: (string | null);
};

