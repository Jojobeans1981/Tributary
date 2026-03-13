"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import NavHeader from "@/app/components/NavHeader";

interface UserProfile {
  id: string;
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
  } | null;
}

interface MeData {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  bio: string;
  district: unknown;
  profile_completion_pct: number;
  has_ferpa_consent: boolean;
  email_preference: string;
}

export default function ProfilePage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [me, setMe] = useState<MeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingBio, setEditingBio] = useState(false);
  const [bioValue, setBioValue] = useState("");
  const [bioError, setBioError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    Promise.all([
      apiFetch<UserProfile>(`/api/users/${id}/`),
      apiFetch<MeData>("/api/users/me/"),
    ]).then(([profileRes, meRes]) => {
      setLoading(false);
      if (profileRes.success && profileRes.data) {
        setProfile(profileRes.data);
        setBioValue(profileRes.data.bio);
      }
      if (meRes.success && meRes.data) {
        setMe(meRes.data);
      }
    });
  }, [id, router]);

  const isOwnProfile = me?.id === id;

  const handleSaveBio = async () => {
    setBioError("");
    const res = await apiFetch<unknown>("/api/users/me/", {
      method: "PATCH",
      body: JSON.stringify({ bio: bioValue }),
    });
    if (!res.success) {
      setBioError(
        typeof res.error?.message === "string"
          ? res.error.message
          : "Failed to update bio."
      );
      return;
    }
    setProfile((prev) => (prev ? { ...prev, bio: bioValue } : prev));
    setEditingBio(false);
  };

  if (loading || !profile) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-2xl mx-auto p-6 space-y-4">
          <div className="bg-sand animate-pulse rounded-full w-12 h-12" />
          <div className="bg-sand animate-pulse rounded-card h-8 w-48" />
          <div className="bg-sand animate-pulse rounded-card h-20" />
        </div>
      </div>
    );
  }

  const initials =
    `${profile.first_name?.[0] || ""}${profile.last_name?.[0] || ""}`.toUpperCase();

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />
      <main className="max-w-2xl mx-auto p-6">
        <div className="bg-chalk rounded-card shadow-card p-6 border border-pebble">
          {/* Avatar + Name */}
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 rounded-full bg-foam text-current font-display font-bold text-lg flex items-center justify-center">
              {initials}
            </div>
            <div>
              <h1 className="font-display text-abyss text-xl font-bold">
                {profile.first_name} {profile.last_name}
              </h1>
              <span className="bg-deep text-white text-xs px-2 py-0.5 rounded-badge">
                {profile.role}
              </span>
            </div>
          </div>

          {/* Bio */}
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-stone mb-1">Bio</h2>
            {editingBio && isOwnProfile ? (
              <div>
                <textarea
                  value={bioValue}
                  onChange={(e) => setBioValue(e.target.value)}
                  maxLength={500}
                  rows={3}
                  className="w-full bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20 text-sm"
                />
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-stone">
                    {bioValue.length}/500
                  </span>
                  {bioError && (
                    <span className="text-xs text-stop">{bioError}</span>
                  )}
                </div>
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={handleSaveBio}
                    className="bg-current text-white font-bold py-1.5 px-4 rounded-input text-sm hover:bg-surface transition-colors duration-150"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => {
                      setEditingBio(false);
                      setBioValue(profile.bio);
                    }}
                    className="border-2 border-current text-current py-1.5 px-4 rounded-input text-sm hover:bg-foam transition-colors duration-150"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-obsidian text-sm">
                  {profile.bio || "No bio yet."}
                </p>
                {isOwnProfile && (
                  <button
                    onClick={() => setEditingBio(true)}
                    className="text-current text-xs mt-1 hover:underline"
                  >
                    Edit bio
                  </button>
                )}
              </div>
            )}
          </div>

          {/* District chip */}
          {profile.district && (
            <Link
              href={`/district/${profile.district.nces_id}`}
              className="inline-flex items-center gap-1 bg-foam text-deep text-sm px-3 py-1 rounded-badge hover:bg-current/10 transition-colors"
            >
              {profile.district.name}, {profile.district.state}
            </Link>
          )}
        </div>
      </main>
    </div>
  );
}
