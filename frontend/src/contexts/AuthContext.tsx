"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { auth as authApi, ApiError } from "@/lib/api";

interface User {
  id: string;
  email: string;
  name: string | null;
  has_password: boolean;
  oauth_providers: string[];
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  clearError: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const setAuthCookie = (loggedIn: boolean) => {
    if (loggedIn) {
      document.cookie = "autollm_logged_in=1; path=/; max-age=86400; samesite=lax";
    } else {
      document.cookie = "autollm_logged_in=; path=/; max-age=0";
    }
  };

  const fetchMe = useCallback(async () => {
    try {
      const data = await authApi.me();
      setUser(data);
      setAuthCookie(true);
    } catch {
      setUser(null);
      setAuthCookie(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const login = async (email: string, password: string) => {
    setError(null);
    try {
      await authApi.login(email, password);
      await fetchMe();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Login failed";
      setError(msg);
      throw e;
    }
  };

  const register = async (email: string, password: string, name?: string) => {
    setError(null);
    try {
      await authApi.register(email, password, name);
      await fetchMe();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Registration failed";
      setError(msg);
      throw e;
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setAuthCookie(false);
    }
  };

  const loginWithGoogle = async () => {
    try {
      const { url } = await authApi.googleUrl();
      window.location.href = url;
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to start Google login";
      setError(msg);
    }
  };

  const refresh = async () => {
    try {
      await authApi.refresh();
      await fetchMe();
    } catch {
      setUser(null);
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider value={{ user, loading, error, login, register, logout, loginWithGoogle, clearError, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
