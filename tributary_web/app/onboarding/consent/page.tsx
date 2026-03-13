"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

export default function ConsentPage() {
  const router = useRouter();
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreed) return;
    setLoading(true);
    setError("");

    const res = await apiFetch<{ user: unknown }>("/api/auth/consent/", {
      method: "POST",
      body: JSON.stringify({ consent_text_version: "1.0" }),
    });

    setLoading(false);

    if (!res.success) {
      setError(
        typeof res.error?.message === "string"
          ? res.error.message
          : "Failed to record consent."
      );
      return;
    }

    router.push("/onboarding/district");
  };

  return (
    <div className="bg-mist min-h-screen flex items-center justify-center px-4">
      <div className="bg-chalk rounded-card shadow-card p-8 w-full max-w-lg border border-pebble">
        <h1 className="font-display text-abyss text-2xl font-bold mb-4">
          Privacy Agreement
        </h1>
        <div className="max-h-64 overflow-y-auto border border-pebble rounded-input p-4 mb-4 text-sm text-slate bg-sand">
          <p className="mb-3">
            <strong>TRIBUTARY Privacy Policy (FERPA Compliance)</strong>
          </p>
          <p className="mb-2">
            TRIBUTARY is committed to protecting the privacy and security of
            all users in accordance with the Family Educational Rights and
            Privacy Act (FERPA).
          </p>
          <p className="mb-2">
            By using this platform, you acknowledge that any educational
            records or personally identifiable information shared through
            TRIBUTARY will be handled in strict accordance with FERPA
            regulations (20 U.S.C. &sect; 1232g; 34 CFR Part 99).
          </p>
          <p className="mb-2">
            We collect only the minimum information necessary to facilitate
            professional community matching among K-12 literacy professionals.
            District-level aggregate data (enrollment, demographics) is sourced
            from the publicly available NCES Common Core of Data.
          </p>
          <p className="mb-2">
            Your personal information will never be sold, shared with
            unauthorized third parties, or used for purposes outside the scope
            of this platform. You retain the right to access, correct, or
            request deletion of your personal data at any time.
          </p>
          <p>
            For the full privacy policy, visit{" "}
            <Link href="/privacy" className="text-current underline">
              our privacy page
            </Link>
            .
          </p>
        </div>
        {error && (
          <div className="bg-stop-light border border-stop text-stop rounded-input px-3 py-2 text-sm mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <label className="flex items-start gap-3 mb-6 cursor-pointer">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="mt-1 w-4 h-4 accent-current"
            />
            <span className="text-sm text-obsidian">
              I have read and accept the TRIBUTARY privacy agreement and
              understand how my data will be used in compliance with FERPA.
            </span>
          </label>
          <button
            type="submit"
            disabled={!agreed || loading}
            className="w-full bg-current text-white font-bold py-3 px-6 rounded-input hover:bg-surface active:bg-deep disabled:bg-pebble disabled:text-stone transition-colors duration-150"
          >
            {loading ? "Submitting..." : "Accept & Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
