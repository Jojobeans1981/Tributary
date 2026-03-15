"use client";

import { useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const res = await apiFetch("/api/auth/password/reset/", {
      method: "POST",
      body: JSON.stringify({ email }),
    });

    setLoading(false);

    if (!res.success) {
      // Always show success to prevent email enumeration
    }
    setSubmitted(true);
  };

  return (
    <div className="bg-mist min-h-screen flex items-center justify-center px-4">
      <div className="bg-chalk rounded-card shadow-card p-8 w-full max-w-md border border-pebble">
        <h1 className="font-display text-abyss text-2xl font-bold mb-2 text-center">
          Reset Password
        </h1>

        {submitted ? (
          <div className="text-center">
            <p className="text-stone text-sm mb-4">
              If an account exists with that email, we&apos;ll send password
              reset instructions.
            </p>
            <Link
              href="/login"
              className="text-current text-sm font-bold hover:underline"
            >
              Back to login
            </Link>
          </div>
        ) : (
          <>
            <p className="text-stone text-sm mb-6 text-center">
              Enter your email and we&apos;ll send you a reset link.
            </p>
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
              <button
                type="submit"
                disabled={loading}
                className="bg-current text-white font-bold py-3 px-6 rounded-input hover:bg-surface active:bg-deep disabled:bg-pebble disabled:text-stone transition-colors duration-150"
              >
                {loading ? "Sending..." : "Send Reset Link"}
              </button>
            </form>
            <div className="mt-4 text-center">
              <Link
                href="/login"
                className="text-current text-sm hover:underline"
              >
                Back to login
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
