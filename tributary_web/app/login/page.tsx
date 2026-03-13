"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { setTokens } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const res = await apiFetch<{
      access: string;
      refresh: string;
      user: { has_ferpa_consent: boolean; has_district: boolean; has_problem_selections: boolean };
    }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    setLoading(false);

    if (!res.success) {
      setError(
        typeof res.error?.message === "string"
          ? res.error.message
          : "Login failed."
      );
      return;
    }

    setTokens(res.data!.access, res.data!.refresh);

    if (!res.data!.user.has_ferpa_consent) {
      router.push("/onboarding/consent");
    } else if (!res.data!.user.has_district) {
      router.push("/onboarding/district");
    } else if (!res.data!.user.has_problem_selections) {
      router.push("/onboarding/problems");
    } else {
      router.push("/dashboard");
    }
  };

  return (
    <div className="bg-mist min-h-screen flex items-center justify-center px-4">
      <div className="bg-chalk rounded-card shadow-card p-8 w-full max-w-md border border-pebble">
        <h1 className="font-display text-abyss text-2xl font-bold mb-6 text-center">
          TRIBUTARY
        </h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <div className="bg-stop-light border border-stop text-stop rounded-input px-3 py-2 text-sm">
              {error}
            </div>
          )}
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-current text-white font-bold py-3 px-6 rounded-input hover:bg-surface active:bg-deep disabled:bg-pebble disabled:text-stone transition-colors duration-150"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
        <div className="mt-4 text-center text-sm text-stone">
          <Link href="/register" className="text-current hover:underline">
            Create an account
          </Link>
          {" | "}
          <Link
            href="/api/auth/password/reset"
            className="text-current hover:underline"
          >
            Forgot password?
          </Link>
        </div>
      </div>
    </div>
  );
}
