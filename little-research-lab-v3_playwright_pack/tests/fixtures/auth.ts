import { expect, type Page } from '@playwright/test';
import { requireEnv } from './env';
import { byTestIdOr } from './locators';

/**
 * UI login using stable locators. Prefer data-testid:
 * - login-email
 * - login-password
 * - login-submit
 *
 * If these don't exist yet, add them to the UI (recommended),
 * or adjust the conservative fallbacks below.
 */
export async function adminLogin(page: Page) {
  const email = requireEnv('ADMIN_EMAIL');
  const password = requireEnv('ADMIN_PASSWORD');

  await page.goto('/login');

  const emailInput = await byTestIdOr(page, 'login-email', [
    () => page.getByLabel(/email/i),
    () => page.getByPlaceholder(/email/i)
  ]);
  const passwordInput = await byTestIdOr(page, 'login-password', [
    () => page.getByLabel(/password/i),
    () => page.getByPlaceholder(/password/i)
  ]);
  const submitBtn = await byTestIdOr(page, 'login-submit', [
    () => page.getByRole('button', { name: /log in|sign in/i })
  ]);

  await emailInput.fill(email);
  await passwordInput.fill(password);
  await submitBtn.click();

  // Dashboard visibility check (minimal)
  await expect(page).toHaveURL(/\/admin(\/)?$/);
}
