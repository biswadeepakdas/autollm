"use client";

import { useState } from "react";
import Link from "next/link";
import { Zap, ArrowLeft, Mail } from "lucide-react";
import { Card, Btn } from "@/components/ui";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${BASE}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) throw new Error("Failed to send reset email");
      setSent(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-sm">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2.5 mb-3">
          <div className="w-11 h-11 bg-gray-900 rounded-2xl flex items-center justify-center shadow-lg">
            <Zap size={22} className="text-white" />
          </div>
          <span className="text-2xl font-extrabold text-gray-900 tracking-tight">AutoLLM</span>
        </div>
        <p className="text-gray-400 text-sm">Reset your password</p>
      </div>

      <Card className="p-7">
        {sent ? (
          <div className="text-center space-y-4">
            <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
              <Mail size={24} className="text-emerald-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Check your email</h3>
            <p className="text-sm text-gray-500">
              If an account with <strong>{email}</strong> exists, we sent a password reset link.
            </p>
            <Link href="/login" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
              Back to sign in
            </Link>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-6">
              Enter your email address and we&apos;ll send you a link to reset your password.
            </p>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition"
                  placeholder="you@company.com"
                />
              </div>
              <Btn type="submit" variant="primary" size="lg" className="w-full" disabled={submitting}>
                {submitting ? "Sending..." : "Send reset link"}
              </Btn>
            </form>

            <div className="mt-4 text-center">
              <Link href="/login" className="text-sm text-gray-500 hover:text-gray-700 inline-flex items-center gap-1">
                <ArrowLeft size={14} /> Back to sign in
              </Link>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
