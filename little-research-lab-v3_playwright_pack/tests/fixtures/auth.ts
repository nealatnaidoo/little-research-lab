import { expect, type Page } from '@playwright/test';
import { ENV } from './env';
import { byTestIdOr } from './locators';

/**
 * Login using dev endpoint for reliable test authentication.
 * Falls back to UI login if dev endpoint is not available.
 */
export async function adminLogin(page: Page) {
  // Try dev login endpoint first (fast, reliable for testing)
  const devLoginUrl = `${ENV.baseURL.replace(':3000', ':8000')}/api/auth/dev/login`;

  try {
    // Make request to dev login endpoint to get auth cookie
    const response = await page.request.get(devLoginUrl, {
      maxRedirects: 0,
    });

    // If dev login works, navigate to admin with the cookie
    if (response.status() === 307 || response.status() === 302) {
      // Cookie should be set, navigate to admin
      await page.goto('/admin');
      await expect(page).toHaveURL(/\/admin(\/)?$/);
      return;
    }
  } catch {
    // Dev endpoint not available, fall back to UI login
  }

  // Fallback: UI login
  await uiLogin(page);
}

/**
 * UI login using stable locators.
 */
async function uiLogin(page: Page) {
  const email = ENV.adminEmail;
  const password = ENV.adminPassword;

  if (!email || !password) {
    throw new Error('ADMIN_EMAIL and ADMIN_PASSWORD env vars required for UI login');
  }

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
