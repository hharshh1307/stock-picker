import { getServerSession } from "next-auth";
import { authOptions } from "@/app/api/auth/[...nextauth]/route";

export async function getSession() {
  return getServerSession(authOptions);
}

export function isAdmin(session: any): boolean {
  return session?.user?.role === "admin";
}

export function isAuthenticated(session: any): boolean {
  return !!session?.user;
}
