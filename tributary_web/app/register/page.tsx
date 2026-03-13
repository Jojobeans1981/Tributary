"use client";

import { useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const res = await apiFetch<{ message: string }>("/api/auth/register/", {
      method: "POST",
      body: JSON.stringify(form),
    });

    setLoading(false);

    if (!res.success) {
      const msg = res.error?.message;
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
      return;
    }

    setSuccess(true);
  };

  if (success) {
    return (
      <div className="bg-mist min-h-screen flex items-center justify-center px-4">
        <div className="bg-chalk rounded-card shadow-card p-8 w-full max-w-md border border-pebble text-center">
          <h1 className="font-display text-abyss text-2xl font-bold mb-4">
            Check Your Email
          </h1>
          <p className="text-slate mb-6">
            We sent a verification link to <strong>{form.email}</strong>. Click
            the link to activate your account.
          </p>
          <Link href="/login" className="text-current hover:underline text-sm">
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen flex items-center justify-center px-4">
      <div className="bg-chalk rounded-card shadow-card p-8 w-full max-w-md border border-pebble">
        <h1 className="font-display text-abyss text-2xl font-bold mb-6 text-center">
          Create Account
        </h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <div className="bg-stop-light border border-stop text-stop rounded-input px-3 py-2 text-sm">
              {error}
            </div>
          )}
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="First name"
              value={form.first_name}
              onChange={(e) =>
                setForm({ ...form, first_name: e.target.value })
              }
              required
              className="bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20 flex-1"
            />
            <input
              type="text"
              placeholder="Last name"
              value={form.last_name}
              onChange={(e) =>
                setForm({ ...form, last_name: e.target.value })
              }
              required
              className="bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20 flex-1"
            />
          </div>
          <input
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
            className="bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20"
          />
          <input
            type="password"
            placeholder="Password (8+ characters)"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
            minLength={8}
            className="bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-current text-white font-bold py-3 px-6 rounded-input hover:bg-surface active:bg-deep disabled:bg-pebble disabled:text-stone transition-colors duration-150"
          >
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-stone">
          Already have an account?{" "}
          <Link href="/login" className="text-current hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
