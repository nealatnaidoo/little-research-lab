import type { Page, Locator } from '@playwright/test';

/**
 * Locator helper that tries a few strategies without inventing selectors:
 * - data-testid (preferred)
 * - label / role / placeholder fallbacks
 *
 * Keep this conservative. If the UI differs, add stable testids rather than expanding brittle fallbacks.
 */
export async function byTestIdOr(page: Page, testId: string, fallbacks: (() => Locator)[]): Promise<Locator> {
  const testIdLoc = page.getByTestId(testId);
  if (await testIdLoc.count()) return testIdLoc;
  for (const fb of fallbacks) {
    const loc = fb();
    if (await loc.count()) return loc;
  }
  // Return the testId locator to produce a useful failure message.
  return testIdLoc;
}
