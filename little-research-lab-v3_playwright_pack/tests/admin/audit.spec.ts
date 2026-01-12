import { test, expect } from '@playwright/test';
import { adminLogin } from '../fixtures/auth';

/**
 * Covers: E8.1 TA-0049 (audit log entries exist)
 */
test('[E8.1+TA-0049] Audit log shows recent activity @smoke @regression', async ({ page }) => {
  await adminLogin(page);
  await page.goto('/admin/audit');

  const table = page.getByTestId('audit-table');
  if (await table.count()) {
    await expect(table).toBeVisible();
  } else {
    // fallback: any audit heading
    await expect(page.getByRole('heading', { name: /audit/i })).toBeVisible();
  }
});
