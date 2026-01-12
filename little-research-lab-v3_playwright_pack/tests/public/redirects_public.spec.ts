import { test, expect } from '@playwright/test';

/**
 * Public redirect behavior verification.
 * NOTE: This assumes a redirect already exists from a prior step or seed.
 * For full determinism, run after creating via admin in the same test run or seed via API.
 */
test('[E7.1+TA-0043] Public redirect returns 301/302 and resolves @smoke @regression', async ({ request }) => {
  // TODO: replace with a seeded redirect path known to exist.
  const from = '/old-seed';
  const res = await request.get(from, { maxRedirects: 0 });
  expect([301, 302, 307, 308]).toContain(res.status());

  const loc = res.headers()['location'];
  expect(loc).toBeTruthy();
});
