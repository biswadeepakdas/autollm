"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Spinner } from "@/components/ui";

/**
 * Google OAuth callback page.
 * The backend redirects here after exchanging the code and setting cookies.
 * We just need to re-fetch the user and redirect to dashboard.
 */
export default function OAuthCallbackPage() {
  const router = useRouter();
  const { refresh } = useAuth();

  useEffect(() => {
    refresh().then(() => {
      router.replace("/dashboard");
    });
  }, [refresh, router]);

  return (
    <div className="flex flex-col items-center gap-3">
      <Spinner className="w-8 h-8" />
      <p className="text-sm text-gray-500">Completing sign in...</p>
    </div>
  );
}
