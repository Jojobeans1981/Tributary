"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import NavHeader from "@/app/components/NavHeader";

interface UserData {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  bio: string;
  district: {
    id: string;
    nces_id: string;
    name: string;
    state: string;
    locale_type: string;
    enrollment: number;
  } | null;
  profile_completion_pct: number;
  has_ferpa_consent: boolean;
  email_preference: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    apiFetch<UserData>("/api/users/me/").then((res) => {
      setLoading(false);
      if (!res.success) {
        if (res.error?.code === "FERPA_CONSENT_REQUIRED") {
          router.replace("/onboarding/consent");
          return;
        }
        router.replace("/login");
        return;
      }
      setUser(res.data!);
    });
  }, [router]);

  if (loading || !user) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-4xl mx-auto p-6 space-y-4">
          <div className="bg-sand animate-pulse rounded-card h-10 w-64" />
          <div className="bg-sand animate-pulse rounded-card h-32" />
          <div className="bg-sand animate-pulse rounded-card h-24" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={user} />
      <main className="max-w-4xl mx-auto p-6">
        <h1 className="font-display text-abyss text-3xl font-bold mb-6">
          Welcome, {user.first_name}
        </h1>

        {/* Profile completion bar */}
        <div className="bg-chalk rounded-card shadow-card p-4 border border-pebble mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-obsidian">
              Profile Completion
            </span>
            <span className="text-sm text-stone">
              {user.profile_completion_pct}%
            </span>
          </div>
          <div className="w-full bg-pebble rounded-full h-2">
            <div
              className="bg-current rounded-full h-2 transition-all duration-300"
              style={{ width: `${user.profile_completion_pct}%` }}
            />
          </div>
          {user.profile_completion_pct < 40 && (
            <Link
              href={`/profile/${user.id}`}
              className="text-current text-sm mt-2 inline-block hover:underline"
            >
              Complete your profile &rarr;
            </Link>
          )}
        </div>

        {/* District card */}
        {user.district ? (
          <Link
            href={`/district/${user.district.nces_id}`}
            className="block bg-chalk rounded-card shadow-card p-4 border border-pebble hover:shadow-card-hover transition-shadow duration-150"
          >
            <h2 className="font-display text-abyss text-xl font-bold">
              {user.district.name}
            </h2>
            <div className="flex gap-3 mt-2 flex-wrap">
              <span className="bg-deep text-white text-xs px-2 py-1 rounded-badge">
                {user.district.locale_type}
              </span>
              <span className="text-sm text-stone">
                {user.district.state}
              </span>
              <span className="text-sm text-stone">
                {user.district.enrollment.toLocaleString()} students
              </span>
            </div>
          </Link>
        ) : (
          <div className="bg-chalk rounded-card shadow-card p-4 border border-pebble">
            <p className="text-stone">No district selected.</p>
            <Link
              href="/onboarding/district"
              className="text-current text-sm mt-1 inline-block hover:underline"
            >
              Select your district &rarr;
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
