import { test, expect } from '@playwright/test';

/**
 * Regression invariant R1: drafts/scheduled content must not be publicly accessible.
 * TODO: make deterministic by creating a draft via admin UI or seed API, then verify 404/403 on public route.
 */
test('[R1] Draft content is not publicly accessible (TODO seed draft) @regression', async ({ request }) => {
  const randomSlug = `definitely-not-a-real-slug-${Date.now()}`;
  const res = await request.get(`/p/${randomSlug}`);
  expect([404, 410]).toContain(res.status());
});
