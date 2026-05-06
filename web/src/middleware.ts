import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import type { NextRequest } from "next/server";

// Routes that require authentication
const PROTECTED_ROUTES = ["/chat", "/portfolio", "/signals", "/settings", "/admin"];
// Routes that require admin role
const ADMIN_ROUTES = ["/admin"];

export async function middleware(request: NextRequest) {
  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  const { pathname } = request.nextUrl;

  const isProtected = PROTECTED_ROUTES.some(r => pathname.startsWith(r));
  const isAdminRoute = ADMIN_ROUTES.some(r => pathname.startsWith(r));

  if (isAdminRoute) {
    if (!token || (token as any).role !== "admin") {
      const url = request.nextUrl.clone();
      url.pathname = token ? "/" : "/login";
      url.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(url);
    }
  } else if (isProtected) {
    if (!token) {
      const url = request.nextUrl.clone();
      url.pathname = "/login";
      url.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(url);
    }
  }

  // Redirect logged-in users away from /login
  if (pathname === "/login" && token) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
