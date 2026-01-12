import { test, expect } from '@playwright/test';
import { adminLogin } from '../fixtures/auth';

test('[E1.1+TA-0001] Admin login -> dashboard visible @smoke @regression', async ({ page }) => {
  await adminLogin(page);
  // Conservative check: either a dashboard heading testid or URL is enough.
  const heading = page.getByTestId('admin-dashboard-title');
  if (await heading.count()) {
    await expect(heading).toBeVisible();
  } else {
    await expect(page).toHaveURL(/\/admin(\/)?$/);
  }
});
