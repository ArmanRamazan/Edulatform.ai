import { test, expect } from "@playwright/test";

// /onboarding is a public path (no auth_token cookie required by middleware),
// but we still set it so the suite is resilient to future auth policy changes.
test.beforeEach(async ({ context }) => {
  await context.addCookies([
    { name: "auth_token", value: "test-token", domain: "localhost", path: "/" },
  ]);
});

test.describe("onboarding", () => {
  test("onboarding wizard loads", async ({ page }) => {
    await page.goto("/onboarding");
    // StepIndicator renders role="progressbar" on mount
    await expect(page.locator('[role="progressbar"]')).toBeVisible();
  });

  test("step indicator starts at step 1", async ({ page }) => {
    await page.goto("/onboarding");
    const indicator = page.locator('[role="progressbar"]');
    await expect(indicator).toBeVisible();
    await expect(indicator).toHaveAttribute("aria-valuenow", "1");
    await expect(indicator).toHaveAttribute("aria-valuemin", "1");
    await expect(indicator).toHaveAttribute("aria-valuemax", "6");
  });
});
