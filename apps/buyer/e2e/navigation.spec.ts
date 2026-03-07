import { test, expect } from "@playwright/test";

test.describe("navigation", () => {
  test("landing page shows hero section", async ({ page }) => {
    await page.goto("/");

    // h1 present — confirms page rendered beyond blank/error state
    await expect(page.locator("h1")).toContainText("Master any tech stack");

    // Primary CTA links are present in the marketing header
    await expect(page.getByRole("link", { name: "Start free" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
  });

  test("sidebar links are present when authenticated", async ({
    page,
    context,
  }) => {
    // ── API stubs ─────────────────────────────────────────────────────────────
    // Stub every endpoint that AppLayout components call on mount so the test
    // is hermetic — no running backend required.

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

    // OrgSwitcher (inside Sidebar) fetches organizations on mount
    await page.route("**/api/identity/organizations**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      })
    );

    // Sidebar notification badge query
    await page.route("**/api/notification/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      })
    );

    // Dashboard block API calls — return empty payloads so blocks show
    // their empty states rather than error states
    await page.route("**/api/learning/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      })
    );
    await page.route("**/api/ai/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      })
    );

    // ── Auth setup ────────────────────────────────────────────────────────────
    // auth_token cookie → bypasses middleware redirect
    // token in localStorage → feeds useAuth hook
    // onboarding_complete → prevents OnboardingGuard redirect to /onboarding
    await context.addCookies([
      { name: "auth_token", value: "test-token", domain: "localhost", path: "/" },
    ]);
    await page.addInitScript(() => {
      localStorage.setItem("token", "test-token");
      localStorage.setItem("onboarding_complete", "true");
    });

    await page.goto("/dashboard");

    // Sidebar <nav> is a semantic landmark — required for screen reader navigation
    await expect(page.locator("nav").first()).toBeVisible();

    // Core navigation links present in the desktop sidebar
    await expect(page.locator('a[href="/dashboard"]').first()).toBeVisible();
    await expect(page.locator('a[href="/missions"]').first()).toBeVisible();
    await expect(page.locator('a[href="/graph"]').first()).toBeVisible();
    await expect(page.locator('a[href="/flashcards"]').first()).toBeVisible();
  });
});
