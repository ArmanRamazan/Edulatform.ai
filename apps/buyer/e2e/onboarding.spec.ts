import { test, expect, type Page } from "@playwright/test";

// Stub every endpoint that AppLayout components (Sidebar, OrgProvider) call
// on mount so the wizard loads without network failures.
async function stubLayoutApis(page: Page) {
  await page.route("**/api/identity/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "test-user-id",
        name: "Test User",
        email: "test@example.com",
        role: "student",
        is_verified: true,
      }),
    })
  );
  await page.route("**/api/identity/organizations**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0 }),
    })
  );
  await page.route("**/api/notification/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0 }),
    })
  );
}

// /onboarding is a public path (no auth_token cookie required by middleware),
// but we still set it so the suite is resilient to future auth policy changes.
// We also init localStorage so useAuth inside Sidebar/OrgProvider gets a token.
test.beforeEach(async ({ context, page }) => {
  await context.addCookies([
    { name: "auth_token", value: "test-token", domain: "localhost", path: "/" },
  ]);
  await page.addInitScript(() => {
    localStorage.setItem("token", "test-token");
  });
});

test.describe("onboarding", () => {
  test("onboarding wizard loads", async ({ page }) => {
    await stubLayoutApis(page);
    await page.goto("/onboarding");

    // StepIndicator renders role="progressbar" on mount
    await expect(page.locator('[role="progressbar"]')).toBeVisible();
  });

  test("step indicator starts at step 1 with correct ARIA attributes", async ({
    page,
  }) => {
    await stubLayoutApis(page);
    await page.goto("/onboarding");

    const indicator = page.locator('[role="progressbar"]');
    await expect(indicator).toBeVisible();

    // Numeric ARIA values let assistive tech announce "Step 1 of 6"
    await expect(indicator).toHaveAttribute("aria-valuenow", "1");
    await expect(indicator).toHaveAttribute("aria-valuemin", "1");
    await expect(indicator).toHaveAttribute("aria-valuemax", "6");

    // aria-label gives screen readers the step name, not just the number
    await expect(indicator).toHaveAttribute(
      "aria-label",
      /Step 1 of 6: Organization/
    );
  });
});
