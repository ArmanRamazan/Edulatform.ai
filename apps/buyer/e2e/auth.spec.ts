import { test, expect } from "@playwright/test";

test.describe("auth pages", () => {
  test("login page loads with form visible", async ({ page }) => {
    await page.goto("/login");

    // Guard against Suspense hanging or unexpected redirect
    await expect(page).toHaveURL("/login");

    // h1 must render — proves the card mounted (no blank/spinner-only screen)
    await expect(
      page.getByRole("heading", { level: 1 })
    ).toBeVisible();

    await expect(page.locator("#email")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();

    // Email field should be autofocused — keyboard-first UX design requirement
    const focusedId = await page.evaluate(
      () => (document.activeElement as HTMLElement | null)?.id ?? ""
    );
    expect(focusedId).toBe("email");
  });

  test("register page loads with form visible", async ({ page }) => {
    await page.goto("/register");

    await expect(page).toHaveURL("/register");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await expect(page.locator("#name")).toBeVisible();
    await expect(page.locator("#email")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();
  });

  test("unauthenticated /dashboard redirects to /login with redirect param", async ({
    page,
  }) => {
    // middleware.ts checks auth_token cookie; if missing, redirects to /login?redirect=...
    // The redirect= param is critical — it ensures the user lands back here after login.
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?redirect=/);
  });
});
