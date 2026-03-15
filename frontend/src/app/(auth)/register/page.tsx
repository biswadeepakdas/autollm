"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Zap, ArrowRight, Eye, EyeOff } from "lucide-react";
import { Card, Btn, GoogleIcon } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";

export default function RegisterPage() {
  const router = useRouter();
  const { register, loginWithGoogle, error, clearError } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await register(email, password, name || undefined);
      router.push("/dashboard");
    } catch {
      // error is set in context
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
        <p className="text-gray-400 text-sm">Auto mode for your SaaS LLM bill</p>
      </div>

      <Card className="p-7">
        <div className="flex bg-gray-100 rounded-xl p-1 mb-6">
          <Link
            href="/login"
            className="flex-1 py-2 text-sm font-semibold rounded-lg text-center text-gray-400 hover:text-gray-600 transition-all"
          >
            Sign in
          </Link>
          <div className="flex-1 py-2 text-sm font-semibold rounded-lg text-center bg-white shadow-sm text-gray-900">
            Create account
          </div>
        </div>

        <button
          onClick={loginWithGoogle}
          className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all"
        >
          <GoogleIcon /> Continue with Google
        </button>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200" /></div>
          <div className="relative flex justify-center"><span className="px-3 bg-white text-xs text-gray-400">or continue with email</span></div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition"
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => { setEmail(e.target.value); clearError(); }}
              className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
            <div className="relative">
              <input
                type={showPw ? "text" : "password"}
                required
                minLength={8}
                value={password}
                onChange={(e) => { setPassword(e.target.value); clearError(); }}
                className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition pr-10"
                placeholder="Min. 8 characters"
              />
              <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          <Btn type="submit" variant="primary" size="lg" className="w-full" disabled={submitting}>
            {submitting ? "Creating account..." : "Create account"}
            {!submitting && <ArrowRight size={16} />}
          </Btn>
        </form>
      </Card>

      <p className="text-center text-xs text-gray-400 mt-6">
        By continuing, you agree to AutoLLM&apos;s Terms of Service and Privacy Policy.
      </p>
    </div>
  );
}
