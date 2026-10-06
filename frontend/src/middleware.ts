import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const DJANGO_API_URL = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const accessToken = request.cookies.get("access_token")?.value;
  const refreshToken = request.cookies.get("refresh_token")?.value;
  const userRole = request.cookies.get("user_role")?.value;

  const isAuthenticated = Boolean(accessToken || refreshToken);

  // If already logged in and trying to view /login, redirect to dashboard
  if (pathname === "/login") {
    if (isAuthenticated) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  // Protected pages require authentication
  if (!isAuthenticated) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Admin-only page protection
  const adminOnlyRoutes = ["/users", "/audit-logs", "/settings"];
  const isAdminRoute = adminOnlyRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );

  if (isAdminRoute) {
    // Strictly deny when userRole !== "ADMIN" (including undefined / missing)
    if (!userRole || userRole !== "ADMIN") {
      const redirectUrl = new URL("/", request.url);
      redirectUrl.searchParams.set("error", "AccessDenied");
      return NextResponse.redirect(redirectUrl);
    }

    // Authoritatively verify role via /api/auth/me/ endpoint if access token is available
    if (accessToken) {
      try {
        const meRes = await fetch(`${DJANGO_API_URL}/auth/me/`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          cache: "no-store",
        });

        if (meRes.ok) {
          const userData = await meRes.json();
          const verifiedRole = userData.is_superuser ? "ADMIN" : userData.role;
          if (verifiedRole !== "ADMIN") {
            const redirectUrl = new URL("/", request.url);
            redirectUrl.searchParams.set("error", "AccessDenied");
            return NextResponse.redirect(redirectUrl);
          }
        } else if (meRes.status === 401) {
          // Access token invalid/expired; redirect to login
          const loginUrl = new URL("/login", request.url);
          loginUrl.searchParams.set("from", pathname);
          return NextResponse.redirect(loginUrl);
        }
      } catch {
        // If external call encounters network error, the strict cookie check above already passed
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, logo images, static assets
     */
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:jpg|jpeg|gif|png|svg|ico)$).*)",
  ],
};
