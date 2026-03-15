"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Zap, Eye, EyeOff, CheckCircle } from "lucide-react";
import { Card, Btn, Spinner } from "@/components/ui";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams?.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);

  useEffect(() => {
    if (!token) {
      setValidating(false);
      return;
    }
    fetch(`${BASE}/api/auth/verify-reset-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then((r) => r.json())
      .then((d) => setTokenValid(d.valid))
      .catch(() => setTokenValid(false))
      .finally(() => setValidating(false));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${BASE}/api/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to reset password");
      }
      setSuccess(true);
      setTimeout(() => router.push("/login"), 3000);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  };

  if (validating) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="w-8 h-8" />
      </div>
    );
  }

  if (!token || !tokenValid) {
    return (
      <Card className="p-7 text-center space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Invalid or expired link</h3>
        <p className="text-sm text-gray-500">This password reset link is invalid or has expired.</p>
        <Link href="/forgot-password" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
          Request a new reset link
        </Link>
      </Card>
    );
  }

  if (success) {
    return (
      <Card className="p-7 text-center space-y-4">
        <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
          <CheckCircle size={24} className="text-emerald-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Password reset!</h3>
        <p className="text-sm text-gray-500">Redirecting you to sign in...</p>
      </Card>
    );
  }

  return (
    <Card className="p-7">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Set new password</h3>
      <p className="text-sm text-gray-500 mb-6">Enter your new password below.</p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">New password</label>
          <div className="relative">
            <input
              type={showPw ? "text" : "password"}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition pr-10"
              placeholder="Min. 8 characters"
            />
            <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Confirm password</label>
          <input
            type="password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition"
            placeholder="Repeat password"
          />
        </div>
        <Btn type="submit" variant="primary" size="lg" className="w-full" disabled={submitting}>
          {submitting ? "Resetting..." : "Reset password"}
        </Btn>
      </form>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="w-full max-w-sm">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2.5 mb-3">
          <div className="w-11 h-11 bg-gray-900 rounded-2xl flex items-center justify-center shadow-lg">
            <Zap size={22} className="text-white" />
          </div>
          <span className="text-2xl font-extrabold text-gray-900 tracking-tight">AutoLLM</span>
        </div>
      </div>
      <Suspense fallback={<div className="flex justify-center"><Spinner className="w-8 h-8" /></div>}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
