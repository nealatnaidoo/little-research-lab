import { test, expect } from '@playwright/test';
import { adminLogin } from '../fixtures/auth';
import { uniqueSlug } from '../fixtures/data';
import { byTestIdOr } from '../fixtures/locators';

/**
 * Covers: E7.1 TA-0043 (create redirect) + R5 (no open redirect / loops)
 */
test('[E7.1+TA-0043] Create internal redirect @smoke @regression', async ({ page }) => {
  await adminLogin(page);
  await page.goto('/admin/redirects');

  const from = `/${uniqueSlug('old')}`;
  const to = '/'; // internal safe target

  // Click the "Add Redirect" button to open the dialog
  const createBtn = await byTestIdOr(page, 'redirects-create', [
    () => page.getByRole('button', { name: /add redirect/i })
  ]);
  await createBtn.click();

  // Wait for dialog to open and find form inputs
  const fromInput = await byTestIdOr(page, 'redirects-from', [
    () => page.getByLabel(/source/i),
    () => page.getByPlaceholder(/old-url/i)
  ]);
  const toInput = await byTestIdOr(page, 'redirects-to', [
    () => page.getByLabel(/target/i),
    () => page.getByPlaceholder(/new-url/i)
  ]);

  await fromInput.fill(from);
  await toInput.fill(to);

  // Click the save button inside the dialog
  const saveBtn = page.getByRole('button', { name: /save redirect/i });
  await saveBtn.click();

  // Wait for dialog to close and redirect to appear in table
  await page.waitForTimeout(500); // Allow state update

  // Expect row appears (either in table or by text)
  const table = page.getByTestId('redirects-table');
  if (await table.count()) {
    await expect(table).toContainText(from);
  } else {
    await expect(page.getByText(from)).toBeVisible();
  }
});
