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
  problem_selection_count: number;
  has_ferpa_consent: boolean;
  email_preference: string;
}

interface ConnectionItem {
  id: string;
  requester: string;
  requester_name: string;
  intro_message: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingConnections, setPendingConnections] = useState<ConnectionItem[]>([]);
  const [justAccepted, setJustAccepted] = useState<ConnectionItem[]>([]);

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

      // Fetch pending incoming connections
      apiFetch<ConnectionItem[]>("/api/connections/?status=PENDING").then(
        (connRes) => {
          if (connRes.success && connRes.data) {
            const incoming = connRes.data.filter(
              (c) => c.requester !== res.data!.id
            );
            setPendingConnections(incoming);
          }
        }
      );
    });
  }, [router]);

  const handleAccept = async (connectionId: string) => {
    const res = await apiFetch(`/api/connections/${connectionId}/`, {
      method: "PATCH",
      body: JSON.stringify({ status: "ACCEPTED" }),
    });
    if (res.success) {
      const accepted = pendingConnections.find((c) => c.id === connectionId);
      setPendingConnections((prev) =>
        prev.filter((c) => c.id !== connectionId)
      );
      if (accepted) {
        setJustAccepted((prev) => [...prev, accepted]);
      }
    }
  };

  const handleMessage = async (userId: string) => {
    await apiFetch<{ id: string }>("/api/conversations/", {
      method: "POST",
      body: JSON.stringify({ participant_id: userId }),
    });
    router.push("/inbox");
  };

  const handleDecline = async (connectionId: string) => {
    const res = await apiFetch(`/api/connections/${connectionId}/`, {
      method: "PATCH",
      body: JSON.stringify({ status: "DECLINED" }),
    });
    if (res.success) {
      setPendingConnections((prev) =>
        prev.filter((c) => c.id !== connectionId)
      );
    }
  };

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
      <main id="main-content" className="max-w-4xl mx-auto p-6">
        <h1 className="font-display text-abyss text-3xl font-bold mb-6">
          Welcome, {user.first_name}
        </h1>

        {/* Pending connection requests */}
        {pendingConnections.length > 0 && (
          <div
            className="bg-chalk rounded-card shadow-card p-4 border border-amber mb-6"
            role="region"
            aria-label="Pending connection requests"
          >
            <h2 className="font-display text-abyss font-bold mb-3">
              Connection Requests ({pendingConnections.length})
            </h2>
            <div className="space-y-3">
              {pendingConnections.map((conn) => (
                <div
                  key={conn.id}
                  className="flex items-center justify-between gap-3 bg-mist rounded-input p-3"
                >
                  <div className="min-w-0">
                    <Link
                      href={`/profile/${conn.requester}`}
                      className="font-display text-abyss font-bold text-sm hover:underline"
                    >
                      {conn.requester_name}
                    </Link>
                    {conn.intro_message && (
                      <p className="text-stone text-xs mt-0.5 truncate">
                        &ldquo;{conn.intro_message}&rdquo;
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => handleAccept(conn.id)}
                      className="bg-go text-white text-xs font-bold px-3 py-1.5 rounded-input hover:opacity-90 transition-colors"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => handleDecline(conn.id)}
                      className="bg-sand text-obsidian text-xs font-bold px-3 py-1.5 rounded-input hover:bg-pebble transition-colors"
                    >
                      Decline
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Just accepted connections */}
        {justAccepted.length > 0 && (
          <div
            className="bg-chalk rounded-card shadow-card p-4 border border-go mb-6"
            role="region"
            aria-label="Accepted connections"
          >
            <h2 className="font-display text-abyss font-bold mb-3">
              New Connections
            </h2>
            <div className="space-y-3">
              {justAccepted.map((conn) => (
                <div
                  key={conn.id}
                  className="flex items-center justify-between gap-3 bg-mist rounded-input p-3"
                >
                  <div className="min-w-0">
                    <Link
                      href={`/profile/${conn.requester}`}
                      className="font-display text-abyss font-bold text-sm hover:underline"
                    >
                      {conn.requester_name}
                    </Link>
                    <p className="text-go text-xs mt-0.5">Connected</p>
                  </div>
                  <button
                    onClick={() => handleMessage(conn.requester)}
                    className="bg-abyss text-white text-xs font-bold px-3 py-1.5 rounded-input hover:opacity-90 transition-colors"
                  >
                    Message
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Profile completion bar */}
        <div
          className="bg-chalk rounded-card shadow-card p-4 border border-pebble mb-6"
          role="region"
          aria-label="Profile completion"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-obsidian">
              Profile Completion
            </span>
            <span className="text-sm text-stone">
              {user.profile_completion_pct}%
            </span>
          </div>
          <div
            className="w-full bg-pebble rounded-full h-2"
            role="progressbar"
            aria-valuenow={user.profile_completion_pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Profile ${user.profile_completion_pct}% complete`}
          >
            <div
              className="bg-current rounded-full h-2 transition-all duration-300"
              style={{ width: `${user.profile_completion_pct}%` }}
            />
          </div>
          {user.profile_completion_pct < 100 && (
            <ul className="mt-3 space-y-1.5 text-sm">
              <CompletionItem
                done={Boolean(user.bio && user.bio.trim())}
                label="Add a bio"
                href={`/profile/${user.id}`}
                points={40}
              />
              <CompletionItem
                done={Boolean(user.district)}
                label="Select your district"
                href="/onboarding/district"
                points={30}
              />
              <CompletionItem
                done={user.problem_selection_count >= 1}
                label="Choose a problem statement"
                href={user.problem_selection_count >= 1 ? "/settings" : "/onboarding/problems"}
                points={20}
              />
              <CompletionItem
                done={user.problem_selection_count >= 2}
                label="Choose a second problem statement"
                href={user.problem_selection_count >= 1 ? "/settings" : "/onboarding/problems"}
                points={10}
              />
            </ul>
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

        {/* Match feed link */}
        <div className="mt-6">
          <Link
            href="/matches"
            className="block bg-current text-white rounded-card shadow-card p-4 text-center hover:bg-deep transition-colors"
          >
            <span className="font-display text-lg font-bold">Find Matches</span>
            <p className="text-foam text-sm mt-1">
              Connect with literacy professionals facing similar challenges
            </p>
          </Link>
        </div>
      </main>
    </div>
  );
}

function CompletionItem({
  done,
  label,
  href,
  points,
}: {
  done: boolean;
  label: string;
  href: string;
  points: number;
}) {
  return (
    <li className="flex items-center gap-2">
      {done ? (
        <svg
          className="w-4 h-4 text-go flex-shrink-0"
          fill="currentColor"
          viewBox="0 0 20 20"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      ) : (
        <svg
          className="w-4 h-4 text-pebble flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 20 20"
          aria-hidden="true"
        >
          <circle cx="10" cy="10" r="7" strokeWidth={2} />
        </svg>
      )}
      {done ? (
        <span className="text-stone line-through">{label}</span>
      ) : (
        <Link href={href} className="text-current hover:underline">
          {label}
        </Link>
      )}
      <span className="text-stone text-xs ml-auto">+{points}%</span>
    </li>
  );
}
