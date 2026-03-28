"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import NavHeader from "@/app/components/NavHeader";

interface MatchedUser {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
  bio: string;
}

interface MatchDistrict {
  name: string;
  state: string;
  locale_type: string;
  enrollment: number;
  frl_pct: string;
  ell_pct: string;
}

interface SharedProblem {
  id: number;
  title: string;
  category: string;
}

interface MatchItem {
  matched_user: MatchedUser;
  district: MatchDistrict | null;
  shared_problems: SharedProblem[];
  demographic_score: number;
  problem_score: number;
  total_score: number;
  connection_status: string;
}

interface MeData {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
}

function ScoreBadge({ score }: { score: number }) {
  let bg = "bg-sand text-abyss border border-pebble";
  let label = "POSSIBLE MATCH";
  if (score >= 80) {
    bg = "bg-current text-white";
    label = "DEEP MATCH";
  } else if (score >= 60) {
    bg = "bg-amber text-white";
    label = "STRONG MATCH";
  } else if (score >= 40) {
    bg = "bg-deep text-white";
    label = "GOOD MATCH";
  }
  return (
    <span className={`${bg} text-xs font-bold px-2 py-1 rounded-badge uppercase`}>
      {label}
    </span>
  );
}

export default function MatchesPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeData | null>(null);
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state
  const [localeTypes, setLocaleTypes] = useState<Set<string>>(new Set());
  const [stateFilter, setStateFilter] = useState("");
  const [minScore, setMinScore] = useState(20);

  // Applied filters (only update on "Apply")
  const [appliedFilters, setAppliedFilters] = useState({
    locale_type: "",
    state: "",
    min_score: 20,
  });

  const fetchMatches = useCallback(
    async (pageNum: number, append: boolean = false) => {
      const params = new URLSearchParams();
      params.set("page", String(pageNum));
      if (appliedFilters.locale_type) params.set("locale_type", appliedFilters.locale_type);
      if (appliedFilters.state) params.set("state", appliedFilters.state);
      if (appliedFilters.min_score > 20) params.set("min_score", String(appliedFilters.min_score));

      const res = await apiFetch<{ results: MatchItem[]; page: number; has_more: boolean }>(
        `/api/matches/?${params.toString()}`
      );
      if (res.success && res.data) {
        if (append) {
          setMatches((prev) => [...prev, ...res.data!.results]);
        } else {
          setMatches(res.data.results);
        }
        setHasMore(res.data.has_more);
        setPage(res.data.page);
      }
      setLoading(false);
    },
    [appliedFilters]
  );

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    apiFetch<MeData>("/api/users/me/").then((res) => {
      if (res.success && res.data) setMe(res.data);
    });

    fetchMatches(1);
  }, [router, fetchMatches]);

  const applyFilters = () => {
    setAppliedFilters({
      locale_type: localeTypes.size === 1 ? Array.from(localeTypes)[0] : "",
      state: stateFilter,
      min_score: minScore,
    });
    setPage(1);
    setLoading(true);
  };

  useEffect(() => {
    if (!loading) return;
    fetchMatches(1);
  }, [appliedFilters, fetchMatches, loading]);

  const handleConnect = async (userId: string) => {
    const res = await apiFetch("/api/connections/", {
      method: "POST",
      body: JSON.stringify({ recipient_id: userId }),
    });
    if (res.success) {
      setMatches((prev) =>
        prev.map((m) =>
          m.matched_user.id === userId
            ? { ...m, connection_status: "PENDING_SENT" }
            : m
        )
      );
    }
  };

  const handleAccept = async (userId: string) => {
    // Find the connection where this user is the requester
    const connRes = await apiFetch<any[]>("/api/connections/?status=PENDING");
    if (connRes.success && connRes.data) {
      const conn = connRes.data.find(
        (c: any) => c.requester === userId
      );
      if (conn) {
        await apiFetch(`/api/connections/${conn.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ status: "ACCEPTED" }),
        });
        setMatches((prev) =>
          prev.map((m) =>
            m.matched_user.id === userId
              ? { ...m, connection_status: "ACCEPTED" }
              : m
          )
        );
      }
    }
  };

  const handleDecline = async (userId: string) => {
    const connRes = await apiFetch<any[]>("/api/connections/?status=PENDING");
    if (connRes.success && connRes.data) {
      const conn = connRes.data.find(
        (c: any) => c.requester === userId
      );
      if (conn) {
        await apiFetch(`/api/connections/${conn.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ status: "DECLINED" }),
        });
        setMatches((prev) =>
          prev.map((m) =>
            m.matched_user.id === userId
              ? { ...m, connection_status: "NONE" }
              : m
          )
        );
      }
    }
  };

  const toggleLocale = (locale: string) => {
    const next = new Set(localeTypes);
    if (next.has(locale)) next.delete(locale);
    else next.add(locale);
    setLocaleTypes(next);
  };

  if (loading) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-4xl mx-auto p-6 space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-sand animate-pulse rounded-card h-48" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />

      <div className="flex">
        {/* Sidebar — desktop */}
        <aside
          className={`${
            showFilters ? "block" : "hidden"
          } md:block w-64 shrink-0 bg-chalk border-r border-pebble p-4 min-h-[calc(100vh-64px)]`}
        >
          <h2 className="font-display text-abyss font-bold mb-3">Filters</h2>

          {/* Locale type */}
          <div className="mb-4">
            <p className="text-stone text-xs font-bold uppercase mb-2">Locale Type</p>
            {["URBAN", "SUBURBAN", "TOWN", "RURAL"].map((l) => (
              <label key={l} className="flex items-center gap-2 mb-1">
                <input
                  type="checkbox"
                  checked={localeTypes.has(l)}
                  onChange={() => toggleLocale(l)}
                  className="accent-current"
                />
                <span className="text-sm text-obsidian">{l}</span>
              </label>
            ))}
          </div>

          {/* State */}
          <div className="mb-4">
            <p className="text-stone text-xs font-bold uppercase mb-2">State</p>
            <input
              type="text"
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value.toUpperCase())}
              placeholder="e.g. OH"
              maxLength={2}
              className="w-full border border-pebble rounded-input px-2 py-1 text-sm"
            />
          </div>

          {/* Min score */}
          <div className="mb-4">
            <p className="text-stone text-xs font-bold uppercase mb-2">
              Min Score: {minScore}
            </p>
            <input
              type="range"
              min={20}
              max={100}
              step={10}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full accent-current"
            />
          </div>

          <button
            onClick={applyFilters}
            className="w-full bg-current text-white text-sm font-bold py-2 rounded-input hover:bg-deep transition-colors"
          >
            Apply Filters
          </button>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6 max-w-4xl">
          <div className="flex items-center justify-between mb-6">
            <h1 className="font-display text-abyss text-2xl font-bold">
              Your Matches
            </h1>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="md:hidden bg-chalk border border-pebble rounded-input px-3 py-1 text-sm text-obsidian"
            >
              Filters
            </button>
          </div>

          {matches.length === 0 ? (
            <div className="bg-chalk rounded-card shadow-card border border-pebble p-8 text-center">
              <p className="text-stone text-sm mb-4">
                Complete your profile to find peer matches.
              </p>
              <Link
                href="/onboarding/problems"
                className="text-current font-bold text-sm hover:underline"
              >
                Select your problem statements
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {matches.map((m) => {
                const user = m.matched_user;
                const initials =
                  `${user.first_name?.[0] || ""}${user.last_name?.[0] || ""}`.toUpperCase();

                return (
                  <div
                    key={user.id}
                    className="relative bg-white rounded-card shadow-card border border-pebble p-4"
                  >
                    {/* Score badge */}
                    <div className="absolute top-3 right-3">
                      <ScoreBadge score={m.total_score} />
                    </div>

                    <div className="flex items-start gap-4">
                      {/* Avatar */}
                      <Link href={`/profile/${user.id}`}>
                        <div className="w-12 h-12 rounded-full bg-foam text-current font-display font-bold text-sm flex items-center justify-center shrink-0">
                          {initials}
                        </div>
                      </Link>

                      <div className="flex-1 min-w-0">
                        <Link href={`/profile/${user.id}`}>
                          <h3 className="font-display text-abyss font-bold">
                            {user.first_name} {user.last_name}
                          </h3>
                        </Link>
                        <p className="text-stone text-xs">{user.role}</p>

                        {m.district && (
                          <p className="text-stone text-xs mt-1">
                            {m.district.name} · {m.district.state} · {m.district.locale_type}
                          </p>
                        )}

                        {user.bio && (
                          <p className="text-slate text-sm mt-2 line-clamp-2">{user.bio}</p>
                        )}

                        {/* Shared problems */}
                        {m.shared_problems.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {m.shared_problems.map((p) => (
                              <span
                                key={p.id}
                                className="bg-foam text-current text-xs px-2 py-1 rounded-badge"
                              >
                                {p.title}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Scores */}
                        <div className="flex gap-3 mt-2 text-xs text-stone">
                          <span>Demo: {m.demographic_score}</span>
                          <span>Problem: {m.problem_score}</span>
                          <span className="font-bold text-abyss">Total: {m.total_score}</span>
                        </div>

                        {/* Connection actions */}
                        <div className="mt-3">
                          {m.connection_status === "NONE" && (
                            <button
                              onClick={() => handleConnect(user.id)}
                              className="bg-current text-white text-sm font-bold px-4 py-1.5 rounded-input hover:bg-deep transition-colors"
                            >
                              Connect
                            </button>
                          )}
                          {m.connection_status === "PENDING_SENT" && (
                            <span className="bg-sand text-stone text-sm font-bold px-4 py-1.5 rounded-input inline-block">
                              Pending
                            </span>
                          )}
                          {m.connection_status === "PENDING_RECEIVED" && (
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleAccept(user.id)}
                                className="bg-go text-white text-sm font-bold px-4 py-1.5 rounded-input hover:opacity-90 transition-colors"
                              >
                                Accept
                              </button>
                              <button
                                onClick={() => handleDecline(user.id)}
                                className="bg-sand text-obsidian text-sm font-bold px-4 py-1.5 rounded-input hover:bg-pebble transition-colors"
                              >
                                Decline
                              </button>
                            </div>
                          )}
                          {m.connection_status === "ACCEPTED" && (
                            <span className="bg-go-light text-go text-sm font-bold px-4 py-1.5 rounded-input inline-block">
                              Connected
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Load more */}
              {hasMore && (
                <div className="text-center pt-4">
                  <button
                    onClick={() => fetchMatches(page + 1, true)}
                    className="bg-chalk border border-pebble text-obsidian text-sm font-bold px-6 py-2 rounded-input hover:shadow-card transition-shadow"
                  >
                    Load more
                  </button>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
