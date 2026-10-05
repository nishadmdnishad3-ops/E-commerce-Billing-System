import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
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
  const isAdminRoute = adminOnlyRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));

  if (isAdminRoute && userRole && userRole !== "ADMIN") {
    // Non-admin attempting to access Admin pages -> redirect to Dashboard
    const redirectUrl = new URL("/", request.url);
    redirectUrl.searchParams.set("error", "AccessDenied");
    return NextResponse.redirect(redirectUrl);
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
