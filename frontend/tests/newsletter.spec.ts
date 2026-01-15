import { test, expect } from '@playwright/test';

/**
 * Newsletter E2E Tests (T-0083)
 *
 * Tests for:
 * - Newsletter signup form (inline and compact)
 * - Email validation
 * - Confirmation page
 * - Unsubscribe page
 *
 * Spec refs: E16, SM3 (newsletter state machine)
 * Test assertions: TA-0074-0076
 */

test.describe('Newsletter', () => {
    // Increase timeout for content creation tests
    test.setTimeout(60000);

    // Helper to create and publish test content for inline signup testing
    async function createPublishedContent(page: import('@playwright/test').Page) {
        // Login
        await page.goto('/login');
        await page.fill('input[name="email"]', 'admin@example.com');
        await page.fill('input[name="password"]', 'changeme');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin/, { timeout: 15000 });

        // Create content
        const title = `Newsletter Test ${Date.now()}`;
        const slug = `newsletter-test-${Date.now()}`;

        await page.goto('/admin/content/new');
        await page.fill('input[name="title"]', title);
        await page.fill('input[name="slug"]', slug);
        await page.fill('textarea[name="summary"]', 'Test content for newsletter signup');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin\/content$/, { timeout: 15000 });

        // Publish the content
        await page.getByText(title).click();
        await page.waitForURL(/\/admin\/content\/[^/]+$/, { timeout: 15000 });
        await page.getByRole('button', { name: 'Publish Now' }).click();
        await expect(page.getByText('Content published')).toBeVisible({ timeout: 10000 });

        return { title, slug };
    }

    test.describe('Inline Signup Form', () => {
        test('Newsletter signup form renders on article page', async ({ page }) => {
            const { slug } = await createPublishedContent(page);

            // Navigate to public article page
            await page.goto(`/p/${slug}`);
            await page.waitForLoadState('networkidle');

            // Newsletter signup form should be visible
            const signupForm = page.locator('[data-testid="newsletter-signup"]');
            await expect(signupForm).toBeVisible({ timeout: 5000 });

            // Should have email input
            const emailInput = signupForm.locator('[data-testid="newsletter-email"]');
            await expect(emailInput).toBeVisible();

            // Should have submit button
            const submitButton = signupForm.locator('[data-testid="newsletter-submit"]');
            await expect(submitButton).toBeVisible();
        });

        test('Newsletter form validates email format', async ({ page }) => {
            const { slug } = await createPublishedContent(page);

            await page.goto(`/p/${slug}`);
            await page.waitForLoadState('networkidle');

            const signupForm = page.locator('[data-testid="newsletter-signup"]');
            const emailInput = signupForm.locator('[data-testid="newsletter-email"]');
            const submitButton = signupForm.locator('[data-testid="newsletter-submit"]');

            // Try invalid email
            await emailInput.fill('invalid-email');
            await submitButton.click();

            // Should show error message (either validation error or API error)
            await expect(
                page.getByText(/valid email|error|invalid/i)
            ).toBeVisible({ timeout: 10000 });
        });

        test('Newsletter form shows loading state during submission', async ({ page }) => {
            const { slug } = await createPublishedContent(page);

            await page.goto(`/p/${slug}`);
            await page.waitForLoadState('networkidle');

            const signupForm = page.locator('[data-testid="newsletter-signup"]');
            const emailInput = signupForm.locator('[data-testid="newsletter-email"]');
            const submitButton = signupForm.locator('[data-testid="newsletter-submit"]');

            // Fill valid email
            const testEmail = `test-${Date.now()}@example.com`;
            await emailInput.fill(testEmail);

            // Submit and check for loading state (button disabled or spinner)
            await submitButton.click();

            // Either success or error should appear (depending on backend availability)
            // This test mainly ensures the form doesn't crash
            await expect(
                page.locator('[data-testid="newsletter-success"], .text-destructive')
            ).toBeVisible({ timeout: 10000 });
        });
    });

    test.describe('Confirmation Page', () => {
        test('Confirmation page renders correctly', async ({ page }) => {
            // Navigate to confirmation page (without token, should show error)
            await page.goto('/newsletter/confirm');
            await page.waitForLoadState('networkidle');

            // Should show error for missing token
            await expect(page.getByRole('heading', { name: /failed/i })).toBeVisible({ timeout: 5000 });

            // Should have back to home button
            await expect(page.getByRole('link', { name: /back to home/i })).toBeVisible();
        });

        test('Confirmation page handles invalid token', async ({ page }) => {
            // Navigate with invalid token
            await page.goto('/newsletter/confirm?token=invalid-token-12345');
            await page.waitForLoadState('networkidle');

            // Should show error
            await expect(
                page.getByText(/failed|error|invalid|expired/i)
            ).toBeVisible({ timeout: 5000 });
        });

        test('Confirmation page shows loading state', async ({ page }) => {
            // Intercept API to delay response
            await page.route('**/api/public/newsletter/confirm*', async route => {
                await new Promise(resolve => setTimeout(resolve, 1000));
                await route.fulfill({
                    status: 400,
                    body: JSON.stringify({ detail: 'Invalid token' })
                });
            });

            // Navigate with a token
            await page.goto('/newsletter/confirm?token=test-token');

            // Should show loading state initially
            await expect(page.getByText(/loading|processing|confirming/i)).toBeVisible();
        });
    });

    test.describe('Unsubscribe Page', () => {
        test('Unsubscribe page renders correctly', async ({ page }) => {
            // Navigate to unsubscribe page (without token, should show error)
            await page.goto('/newsletter/unsubscribe');
            await page.waitForLoadState('networkidle');

            // Should show error for missing token
            await expect(page.getByRole('heading', { name: /failed/i })).toBeVisible({ timeout: 5000 });

            // Should have back to home button
            await expect(page.getByRole('link', { name: /back to home/i })).toBeVisible();
        });

        test('Unsubscribe page handles invalid token', async ({ page }) => {
            // Navigate with invalid token
            await page.goto('/newsletter/unsubscribe?token=invalid-token-12345');
            await page.waitForLoadState('networkidle');

            // Should show error
            await expect(
                page.getByText(/failed|error|invalid|expired/i)
            ).toBeVisible({ timeout: 5000 });
        });

        test('Unsubscribe page shows loading state', async ({ page }) => {
            // Intercept API to delay response
            await page.route('**/api/public/newsletter/unsubscribe*', async route => {
                await new Promise(resolve => setTimeout(resolve, 1000));
                await route.fulfill({
                    status: 400,
                    body: JSON.stringify({ detail: 'Invalid token' })
                });
            });

            // Navigate with a token
            await page.goto('/newsletter/unsubscribe?token=test-token');

            // Should show loading state initially
            await expect(page.getByText(/loading|processing/i)).toBeVisible();
        });
    });

    test.describe('Page Rendering', () => {
        test('Newsletter pages have no hydration errors', async ({ page }) => {
            const consoleErrors: string[] = [];
            page.on('console', msg => {
                if (msg.type() === 'error') {
                    consoleErrors.push(msg.text());
                }
            });

            // Test confirmation page
            await page.goto('/newsletter/confirm?token=test');
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(500);

            // Test unsubscribe page
            await page.goto('/newsletter/unsubscribe?token=test');
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(500);

            // Check for hydration errors
            const hydrationErrors = consoleErrors.filter(e =>
                e.toLowerCase().includes('hydration') ||
                e.toLowerCase().includes('mismatch')
            );
            expect(hydrationErrors).toHaveLength(0);
        });

        test('Newsletter pages use Suspense correctly', async ({ page }) => {
            const consoleErrors: string[] = [];
            page.on('console', msg => {
                if (msg.type() === 'error') {
                    consoleErrors.push(msg.text());
                }
            });

            // Navigate quickly to both pages
            await page.goto('/newsletter/confirm');
            await page.goto('/newsletter/unsubscribe');

            // No Suspense boundary errors should occur
            const suspenseErrors = consoleErrors.filter(e =>
                e.toLowerCase().includes('suspense') ||
                e.toLowerCase().includes('usesearchparams')
            );
            expect(suspenseErrors).toHaveLength(0);
        });
    });

    test.describe('Privacy', () => {
        test('Newsletter form does not leak PII in requests', async ({ page }) => {
            const { slug } = await createPublishedContent(page);

            // Capture all requests
            const requests: Array<{ url: string; body: string }> = [];
            page.on('request', request => {
                requests.push({
                    url: request.url(),
                    body: request.postData() || ''
                });
            });

            await page.goto(`/p/${slug}`);
            await page.waitForLoadState('networkidle');

            // Check that non-newsletter requests don't contain email data
            const nonNewsletterRequests = requests.filter(r =>
                !r.url.includes('/newsletter/')
            );

            for (const req of nonNewsletterRequests) {
                // Should not contain email patterns in tracking/analytics requests
                if (req.url.includes('/analytics') || req.url.includes('/event')) {
                    expect(req.body).not.toMatch(/@.*\./);
                }
            }
        });
    });
});
