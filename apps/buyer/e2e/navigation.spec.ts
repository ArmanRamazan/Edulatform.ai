import { test, expect } from "@playwright/test";

test.describe("navigation", () => {
  test("landing page shows hero section", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Master any tech stack");
  });

  test("sidebar links are present when authenticated", async ({
    page,
    context,
  }) => {
    // Stub backend calls so the test doesn't require a running API server
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
    await page.route("**/api/notification/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      })
    );

    // auth_token cookie bypasses middleware; token in localStorage feeds useAuth hook;
    // onboarding_complete prevents OnboardingGuard from redirecting to /onboarding
    await context.addCookies([
      { name: "auth_token", value: "test-token", domain: "localhost", path: "/" },
    ]);
    await page.addInitScript(() => {
      localStorage.setItem("token", "test-token");
      localStorage.setItem("onboarding_complete", "true");
    });

    await page.goto("/dashboard");
    await expect(page.locator('a[href="/dashboard"]').first()).toBeVisible();
    await expect(page.locator('a[href="/missions"]').first()).toBeVisible();
  });
});
