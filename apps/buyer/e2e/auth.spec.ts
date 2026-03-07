import { test, expect } from "@playwright/test";

test.describe("auth pages", () => {
  test("login page loads with form visible", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("#email")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();
    await expect(page.getByRole("button", { name: /войти/i })).toBeVisible();
  });

  test("register page loads with form visible", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator("#name")).toBeVisible();
    await expect(page.locator("#email")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();
  });

  test("dashboard without auth redirects to login", async ({ page }) => {
    // middleware.ts checks auth_token cookie; if missing, redirects to /login?redirect=...
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });
});
