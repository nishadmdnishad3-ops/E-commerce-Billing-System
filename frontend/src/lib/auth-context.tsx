"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api, User } from "./api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, pass: string) => Promise<void>;
  logout: () => Promise<void>;
  changePassword: (data: { old_password: string; new_password: string; confirm_password: string }) => Promise<void>;
  isAdmin: boolean;
  isAccountant: boolean;
  isStaff: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
  changePassword: async () => {},
  isAdmin: false,
  isAccountant: false,
  isStaff: false,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    async function loadUser() {
      if (pathname === "/login") {
        setLoading(false);
        return;
      }

      try {
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
      } catch (err) {
        setUser(null);
        if (pathname !== "/login") {
          router.push(`/login?from=${encodeURIComponent(pathname)}`);
        }
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [pathname, router]);

  const login = async (username: string, pass: string) => {
    const res = await api.login(username, pass);
    if (res.user) {
      setUser(res.user);
    } else {
      const currentUser = await api.getCurrentUser();
      setUser(currentUser);
    }

    const params = new URLSearchParams(window.location.search);
    const redirectTo = params.get("from") || "/";
    router.push(redirectTo);
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    router.push("/login");
  };

  const changePassword = async (data: { old_password: string; new_password: string; confirm_password: string }) => {
    await api.changePassword(data);
  };

  const isAdmin = user?.role === "ADMIN" || Boolean(user?.is_superuser);
  const isAccountant = isAdmin || user?.role === "ACCOUNTANT";
  const isStaff = user?.role === "STAFF";

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        changePassword,
        isAdmin,
        isAccountant,
        isStaff,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
