import { test, expect } from '@playwright/test';

/**
 * Content Lifecycle E2E Tests
 *
 * Tests the complete content workflow:
 * - Create draft content
 * - Edit content
 * - Schedule content for future publication
 * - Unschedule content
 * - Publish content immediately
 * - Unpublish content
 * - Delete content
 */

test.describe('Content Lifecycle', () => {
    const testContent = {
        title: `Test Post ${Date.now()}`,
        slug: `test-post-${Date.now()}`,
        description: 'E2E test content for lifecycle testing',
    };

    // Login before each test
    test.beforeEach(async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[name="email"]', 'admin@example.com');
        await page.fill('input[name="password"]', 'changeme');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin/, { timeout: 10000 });
    });

    test('Create new draft content', async ({ page }) => {
        // Navigate to new content page
        await page.goto('/admin/content/new');

        // Fill in content details
        await page.fill('input[name="title"]', testContent.title);
        await page.fill('input[name="slug"]', testContent.slug);
        await page.fill('textarea[name="summary"]', testContent.description);

        // Submit form
        await page.click('button[type="submit"]');

        // Should redirect to content list
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });

        // Verify content appears in list
        await expect(page.getByText(testContent.title)).toBeVisible();
    });

    test('Edit existing content', async ({ page }) => {
        // First create content
        await page.goto('/admin/content/new');
        await page.fill('input[name="title"]', testContent.title);
        await page.fill('input[name="slug"]', testContent.slug);
        await page.fill('textarea[name="summary"]', testContent.description);
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });

        // Click on the content to edit
        await page.getByText(testContent.title).click();
        await page.waitForURL(/\/admin\/content\/[^/]+$/, { timeout: 10000 });

        // Update title
        const newTitle = `${testContent.title} - Updated`;
        await page.fill('input[name="title"]', newTitle);

        // Save draft
        await page.getByRole('button', { name: 'Save Draft' }).click();

        // Verify save toast or updated content
        await expect(page.getByText('Content saved')).toBeVisible({ timeout: 5000 });
    });

    test('Publish content immediately', async ({ page }) => {
        // Create content first
        await page.goto('/admin/content/new');
        const publishTitle = `Publish Test ${Date.now()}`;
        const publishSlug = `publish-test-${Date.now()}`;

        await page.fill('input[name="title"]', publishTitle);
        await page.fill('input[name="slug"]', publishSlug);
        await page.fill('textarea[name="summary"]', 'Test for immediate publish');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });

        // Navigate to edit the content
        await page.getByText(publishTitle).click();
        await page.waitForURL(/\/admin\/content\/[^/]+$/, { timeout: 10000 });

        // Click Publish Now
        await page.getByRole('button', { name: 'Publish Now' }).click();

        // Verify published status
        await expect(page.getByText('Content published')).toBeVisible({ timeout: 5000 });
        // Check for the status badge (use exact match)
        await expect(page.locator('[data-slot="badge"]').getByText('Published', { exact: true })).toBeVisible();
    });

    test('Schedule content for later', async ({ page }) => {
        // Create content first
        await page.goto('/admin/content/new');
        const scheduleTitle = `Schedule Test ${Date.now()}`;
        const scheduleSlug = `schedule-test-${Date.now()}`;

        await page.fill('input[name="title"]', scheduleTitle);
        await page.fill('input[name="slug"]', scheduleSlug);
        await page.fill('textarea[name="summary"]', 'Test for scheduling');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });

        // Navigate to edit
        await page.getByText(scheduleTitle).click();
        await page.waitForURL(/\/admin\/content\/[^/]+$/, { timeout: 10000 });

        // Click Schedule for Later
        await page.getByRole('button', { name: 'Schedule for Later' }).click();

        // Set future date (tomorrow)
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const dateStr = tomorrow.toISOString().slice(0, 16);
        await page.fill('input[type="datetime-local"]', dateStr);

        // Click Schedule
        await page.getByRole('button', { name: 'Schedule' }).click();

        // Verify scheduled status
        await expect(page.getByText('Content scheduled')).toBeVisible({ timeout: 5000 });
    });

    test('Unschedule scheduled content', async ({ page }) => {
        // Create and schedule content first
        await page.goto('/admin/content/new');
        const unscheduleTitle = `Unschedule Test ${Date.now()}`;
        const unscheduleSlug = `unschedule-test-${Date.now()}`;

        await page.fill('input[name="title"]', unscheduleTitle);
        await page.fill('input[name="slug"]', unscheduleSlug);
        await page.fill('textarea[name="summary"]', 'Test for unscheduling');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });

        // Navigate and schedule
        await page.getByText(unscheduleTitle).click();
        await page.waitForURL(/\/admin\/content\/[^/]+$/, { timeout: 10000 });

        await page.getByRole('button', { name: 'Schedule for Later' }).click();
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        await page.fill('input[type="datetime-local"]', tomorrow.toISOString().slice(0, 16));
        await page.getByRole('button', { name: 'Schedule' }).click();
        await expect(page.getByText('Content scheduled')).toBeVisible({ timeout: 10000 });

        // Wait for status to update to Scheduled
        await expect(page.locator('[data-slot="badge"]').getByText('Scheduled', { exact: true })).toBeVisible({ timeout: 5000 });

        // Now unschedule
        await page.getByRole('button', { name: 'Unschedule' }).click();

        // Confirm in dialog
        await page.getByRole('button', { name: 'Unschedule' }).last().click();

        // Verify back to draft
        await expect(page.getByText('Publication cancelled')).toBeVisible({ timeout: 5000 });
    });

    test('Unpublish published content', async ({ page }) => {
        // Create and publish content first
        await page.goto('/admin/content/new');
        const unpublishTitle = `Unpublish Test ${Date.now()}`;
        const unpublishSlug = `unpublish-test-${Date.now()}`;

        await page.fill('input[name="title"]', unpublishTitle);
        await page.fill('input[name="slug"]', unpublishSlug);
        await page.fill('textarea[name="summary"]', 'Test for unpublishing');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });

        // Navigate and publish
        await page.getByText(unpublishTitle).click();
        await page.waitForURL(/\/admin\/content\/[^/]+$/, { timeout: 10000 });

        await page.getByRole('button', { name: 'Publish Now' }).click();
        await expect(page.getByText('Content published')).toBeVisible({ timeout: 5000 });

        // Now unpublish
        await page.getByRole('button', { name: 'Unpublish' }).click();

        // Confirm in dialog
        await page.getByRole('button', { name: 'Unpublish' }).last().click();

        // Verify back to draft
        await expect(page.getByText('Content unpublished')).toBeVisible({ timeout: 5000 });
    });

    test('Delete draft content', async ({ page }) => {
        // Create content first
        await page.goto('/admin/content/new');
        const deleteTitle = `Delete Test ${Date.now()}`;
        const deleteSlug = `delete-test-${Date.now()}`;

        await page.fill('input[name="title"]', deleteTitle);
        await page.fill('input[name="slug"]', deleteSlug);
        await page.fill('textarea[name="summary"]', 'Test for deletion');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });

        // Navigate to edit
        await page.getByText(deleteTitle).click();
        await page.waitForURL(/\/admin\/content\/[^/]+$/, { timeout: 10000 });

        // Click delete button (trash icon)
        await page.locator('button:has(svg.lucide-trash-2)').click();

        // Confirm deletion
        await page.getByRole('button', { name: 'Delete' }).last().click();

        // Verify deleted and redirected
        await expect(page.getByText('Content deleted')).toBeVisible({ timeout: 5000 });
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });
    });

    test('Cannot delete published content', async ({ page }) => {
        // Create and publish content
        await page.goto('/admin/content/new');
        const protectedTitle = `Protected Test ${Date.now()}`;
        const protectedSlug = `protected-test-${Date.now()}`;

        await page.fill('input[name="title"]', protectedTitle);
        await page.fill('input[name="slug"]', protectedSlug);
        await page.fill('textarea[name="summary"]', 'Test protected from deletion');
        await page.click('button[type="submit"]');
        await page.waitForURL(/\/admin\/content$/, { timeout: 10000 });

        // Navigate and publish
        await page.getByText(protectedTitle).click();
        await page.waitForURL(/\/admin\/content\/[^/]+$/, { timeout: 10000 });

        await page.getByRole('button', { name: 'Publish Now' }).click();
        await expect(page.getByText('Content published')).toBeVisible({ timeout: 5000 });

        // Try to delete - should fail
        await page.locator('button:has(svg.lucide-trash-2)').click();
        await page.getByRole('button', { name: 'Delete' }).last().click();

        // Verify error toast appears (the toast will show "Failed to delete content")
        await expect(page.getByText(/Failed to delete|delete failed/i)).toBeVisible({ timeout: 5000 });
    });

    test('Content list shows correct status badges', async ({ page }) => {
        await page.goto('/admin/content');

        // Check status tabs exist
        await expect(page.getByRole('tab', { name: /All/i })).toBeVisible();
        await expect(page.getByRole('tab', { name: /Drafts/i })).toBeVisible();
        await expect(page.getByRole('tab', { name: /Scheduled/i })).toBeVisible();
        await expect(page.getByRole('tab', { name: /Published/i })).toBeVisible();
    });

    test('Filter content by status', async ({ page }) => {
        await page.goto('/admin/content');

        // Click on Drafts tab
        await page.getByRole('tab', { name: /Drafts/i }).click();

        // All visible items should be drafts (or empty state)
        const rows = page.locator('table tbody tr');
        const count = await rows.count();

        if (count > 0) {
            // Each row should have Draft badge
            for (let i = 0; i < Math.min(count, 3); i++) {
                const row = rows.nth(i);
                await expect(row.getByText('Draft')).toBeVisible();
            }
        }
    });
});
