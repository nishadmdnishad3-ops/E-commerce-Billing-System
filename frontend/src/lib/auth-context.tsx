"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api, User } from "./api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, pass: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
  isAccountant: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
  isAdmin: false,
  isAccountant: false,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    async function loadUser() {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      if (!token) {
        setLoading(false);
        if (pathname !== "/login") {
          router.push("/login");
        }
        return;
      }

      try {
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
      } catch (err) {
        console.error("Failed to load authenticated user:", err);
        api.logout();
        if (pathname !== "/login") {
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [pathname, router]);

  const login = async (username: string, pass: string) => {
    await api.login(username, pass);
    const currentUser = await api.getCurrentUser();
    setUser(currentUser);
    router.push("/");
  };

  const logout = () => {
    api.logout();
    setUser(null);
    router.push("/login");
  };

  const isAdmin = user?.role === "ADMIN" || !!user?.is_superuser;
  const isAccountant = isAdmin || user?.role === "ACCOUNTANT";

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAdmin, isAccountant }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
