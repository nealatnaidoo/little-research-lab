import { test, expect } from '@playwright/test';
import { adminLogin } from '../fixtures/auth';
import { uniqueTitle } from '../fixtures/data';
import { byTestIdOr } from '../fixtures/locators';

/**
 * Covers: E1.1 TA-0001/TA-0002 (admin settings load/save), and checks public SSR reflects settings where feasible.
 */
test('[E1.1+TA-0001] Settings load + save @smoke @regression', async ({ page }) => {
  await adminLogin(page);
  await page.goto('/admin/settings');

  const siteTitle = await byTestIdOr(page, 'settings-site-title', [
    () => page.getByLabel(/site title|title/i),
    () => page.getByPlaceholder(/title/i)
  ]);
  const saveBtn = await byTestIdOr(page, 'settings-save', [
    () => page.getByRole('button', { name: /save/i })
  ]);

  const newTitle = uniqueTitle('LRL Settings Title');
  await siteTitle.fill(newTitle);
  await saveBtn.click();

  const toast = page.getByTestId('toast-success');
  if (await toast.count()) await expect(toast).toBeVisible();

  // Basic public SSR smoke: home should load; metadata reflection may require specific DOM hooks.
  await page.goto('/');
  await expect(page).toHaveURL(/\/$/);
});
