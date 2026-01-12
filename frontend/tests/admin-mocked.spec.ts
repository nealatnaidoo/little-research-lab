import { test, expect } from '@playwright/test';

test.describe('Admin UI Suite', () => {

    // Mock API responses before each test
    test.beforeEach(async ({ page }) => {
        // Mock Login
        await page.route('/api/auth/login', async route => {
            await route.fulfill({ json: { access_token: 'fake-token', token_type: 'bearer' } });
        });

        // Mock User Info
        await page.route('/api/auth/me', async route => {
            await route.fulfill({ json: { id: 'admin-id', email: 'admin@example.com', role: 'admin' } });
        });

        // Mock Content List
        await page.route('/api/content*', async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({ json: { items: [], total: 0, page: 1, size: 50 } });
            } else {
                await route.continue();
            }
        });

        // Mock Audit Log
        await page.route('/api/admin/audit*', async route => {
            await route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 20 } });
        });

        // Mock Redirects
        await page.route('/api/admin/redirects/redirects*', async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({ json: { redirects: [], count: 0 } });
            } else {
                await route.continue();
            }
        });

        // Validate Redirects
        await page.route('/api/admin/redirects/redirects/validate', async route => {
            await route.fulfill({ json: { valid: true, issues: [], total_checked: 0 } });
        });
    });

    test('Admin Dashboard Redirection', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[name="email"]', 'admin@example.com');
        await page.fill('input[name="password"]', 'password');
        await page.click('button[type="submit"]');

        // Should redirect to admin (or dashboard) - assuming login page handles redirect
        // Since we mocked the API, we expect a client-side transition
        await expect(page).toHaveURL(/\/admin/);
    });

    test('Redirects Management Page Loads', async ({ page }) => {
        // Bypass login by setting token (if specific mechanism used) or just relying on mocked /me
        // But most likely we need to do the login flow or mock the session state.
        // Simplified: Just visit page and expect it to load (assuming middleware mocks or public for now, or we do login first)

        // Do Login
        await page.goto('/login');
        await page.fill('input[name="email"]', 'admin@example.com');
        await page.fill('input[name="password"]', 'password');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin/);

        // Navigate to Redirects
        await page.goto('/admin/redirects');

        // Check Header
        await expect(page.getByRole('heading', { name: 'Redirects' })).toBeVisible();
        await expect(page.getByText('Manage URL redirects')).toBeVisible();

        // Check "Add Redirect" button
        await expect(page.getByRole('button', { name: 'Add Redirect' })).toBeVisible();
    });

    test('Audit Log Page Loads', async ({ page }) => {
        await page.goto('/login');
        // Login...
        await page.fill('input[name="email"]', 'admin@example.com');
        await page.fill('input[name="password"]', 'password');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin/);

        await page.goto('/admin/audit');
        await expect(page.getByText('Audit Log')).toBeVisible();
        await expect(page.getByRole('table')).toBeVisible();
    });

    test('Create Redirect Flow', async ({ page }) => {
        // Login
        await page.goto('/login');
        await page.fill('input[name="email"]', 'admin@example.com');
        await page.fill('input[name="password"]', 'password');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin/);

        await page.goto('/admin/redirects');

        // Mock Create response
        // Initial Mock: Empty List
        await page.route('/api/admin/redirects/redirects*', async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({ json: { redirects: [], count: 0 } });
            } else if (route.request().method() === 'POST') {
                await route.fulfill({
                    json: {
                        id: 'new-id',
                        source_path: '/foo',
                        target_path: '/bar',
                        status_code: 301,
                        enabled: true,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    }
                });
            } else {
                await route.continue();
            }
        });

        // Ensure initial load complete
        await expect(page.getByText('No redirects configured')).toBeVisible();

        await page.getByRole('button', { name: 'Add Redirect' }).click();
        await page.fill('input[name="source_path"]', '/foo');
        await page.fill('input[name="target_path"]', '/bar');

        // Override GET mock for the update that happens after save
        await page.route('/api/admin/redirects/redirects*', async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({
                    json: {
                        redirects: [{
                            id: 'new-id',
                            source_path: '/foo',
                            target_path: '/bar',
                            status_code: 301,
                            enabled: true,
                            created_at: new Date().toISOString(),
                            updated_at: new Date().toISOString()
                        }], count: 1
                    }
                });
            } else if (route.request().method() === 'POST') { // Keep POST mock working
                await route.fulfill({
                    json: { id: 'new-id', source_path: '/foo', target_path: '/bar', status_code: 301, enabled: true, created_at: new Date(), updated_at: new Date() }
                });
            } else {
                await route.continue();
            }
        });



        await page.getByRole('button', { name: 'Save Redirect' }).click();

        // Expect validation toast or table update
        await expect(page.getByText('/foo')).toBeVisible();
        await expect(page.getByText('/bar')).toBeVisible();
    });

});
