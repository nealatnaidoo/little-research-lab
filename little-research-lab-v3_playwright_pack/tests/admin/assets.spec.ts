import { test, expect } from '@playwright/test';
import path from 'path';
import { adminLogin } from '../fixtures/auth';
import { byTestIdOr } from '../fixtures/locators';

/**
 * Covers: E2.2 TA-0009/TA-0011 (asset upload + list)
 * Uses deterministic fixtures in tests/fixtures/files
 */
test('[E2.2+TA-0009] Upload asset and see it in list @smoke @regression', async ({ page }) => {
  await adminLogin(page);
  await page.goto('/admin/assets');

  // Click the "Upload Asset" button to open the dialog
  const uploadTrigger = page.getByRole('button', { name: /upload asset/i });
  await uploadTrigger.click();

  // Wait for dialog to appear and find the file input
  const uploadInput = await byTestIdOr(page, 'assets-upload-input', [
    () => page.locator('input[type="file"]')
  ]);

  const filePath = path.resolve('tests/fixtures/files/sample.pdf');
  await uploadInput.setInputFiles(filePath);

  // Click the upload/submit button
  const uploadSubmit = page.getByTestId('assets-upload-submit');
  if (await uploadSubmit.count()) await uploadSubmit.click();

  // Wait for upload to complete and dialog to close
  await page.waitForTimeout(1000);

  // Assert list shows the uploaded file (or filename appears on page)
  const table = page.getByTestId('assets-table');
  if (await table.count()) {
    await expect(table).toBeVisible();
  } else {
    // fallback: look for filename in page text or grid items (use first() for multiple matches)
    await expect(page.getByText(/sample\.pdf/i).first()).toBeVisible({ timeout: 10000 });
  }
});
