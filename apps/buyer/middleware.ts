import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Paths that never require authentication
const PUBLIC_PATHS = new Set([
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/verify-email",
  "/reset-password",
  "/welcome",
  "/onboarding",
]);

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_PATHS.has(pathname)) return true;

  // Next.js internals, API proxy routes, and static assets
  if (
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/api/") ||
    pathname === "/favicon.ico" ||
    /\.(?:png|jpe?g|gif|svg|ico|webp|woff2?|ttf|otf|eot)$/.test(pathname)
  ) {
    return true;
  }

  return false;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // Middleware only checks cookie existence — JWT validity is enforced by api-gateway
  const token = request.cookies.get("auth_token")?.value;

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Skip Next.js static file serving — handled by isPublicPath above for anything else
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
