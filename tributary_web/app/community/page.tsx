"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import NavHeader from "@/app/components/NavHeader";

/* ---------- types ---------- */

interface MeData {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
}

interface District {
  name: string;
  state: string;
  locale_type: string;
}

interface ProblemSelection {
  title: string;
  category: string;
}

interface MemberItem {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
  bio_excerpt: string;
  district: District | null;
  problem_selections: ProblemSelection[];
  match_score: number;
  connection_status: string;
  is_featured: boolean;
}

interface CommunityResponse {
  results: MemberItem[];
  total_count: number;
  page: number;
  has_more: boolean;
}

/* ---------- component ---------- */

export default function CommunityPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeData | null>(null);
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  /* filters */
  const [search, setSearch] = useState("");
  const [state, setState] = useState("");
  const [localeType, setLocaleType] = useState("");
  const [sort, setSort] = useState("match_score");

  /* auth */
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }
    apiFetch<MeData>("/api/users/me/").then((res) => {
      if (res.success && res.data) setMe(res.data);
    });
  }, [router]);

  /* fetch members */
  const fetchMembers = useCallback(
    (p: number) => {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("page", String(p));
      params.set("sort", sort);
      if (search) params.set("search", search);
      if (state) params.set("state", state);
      if (localeType) params.set("locale_type", localeType);

      apiFetch<CommunityResponse>(`/api/community/?${params}`).then((res) => {
        if (res.success && res.data) {
          setMembers(res.data.results);
          setTotalCount(res.data.total_count);
          setHasMore(res.data.has_more);
          setPage(res.data.page);
        }
        setLoading(false);
      });
    },
    [search, state, localeType, sort]
  );

  useEffect(() => {
    if (me) fetchMembers(1);
  }, [me, fetchMembers]);

  /* connection action */
  const handleConnect = async (memberId: string) => {
    const res = await apiFetch("/api/connections/", {
      method: "POST",
      body: JSON.stringify({ recipient_id: memberId }),
    });
    if (res.success) {
      setMembers((prev) =>
        prev.map((m) =>
          m.id === memberId ? { ...m, connection_status: "PENDING_SENT" } : m
        )
      );
    }
  };

  const connectionBadge = (status: string) => {
    switch (status) {
      case "ACCEPTED":
        return (
          <span className="bg-go-light text-go text-xs font-bold px-2 py-0.5 rounded-badge">
            Connected
          </span>
        );
      case "PENDING_SENT":
        return (
          <span className="bg-amber-light text-amber text-xs font-bold px-2 py-0.5 rounded-badge">
            Pending
          </span>
        );
      case "PENDING_RECEIVED":
        return (
          <span className="bg-current/10 text-current text-xs font-bold px-2 py-0.5 rounded-badge">
            Respond
          </span>
        );
      default:
        return null;
    }
  };

  if (!me) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-6xl mx-auto p-6 space-y-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-sand animate-pulse rounded-card h-24" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />

      <main id="main-content" className="max-w-6xl mx-auto p-6" aria-label="Community directory">
        <h1 className="font-display text-abyss text-2xl font-bold mb-6">
          Community Directory
        </h1>

        {/* Filters */}
        <div className="bg-chalk rounded-card border border-pebble p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input
              type="text"
              placeholder="Search by name or district..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search members by name or district"
              className="border border-pebble rounded-input px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="State (e.g. CA)"
              value={state}
              onChange={(e) => setState(e.target.value)}
              aria-label="Filter by state"
              className="border border-pebble rounded-input px-3 py-2 text-sm"
            />
            <select
              value={localeType}
              onChange={(e) => setLocaleType(e.target.value)}
              aria-label="Filter by locale type"
              className="border border-pebble rounded-input px-3 py-2 text-sm bg-white"
            >
              <option value="">All Locale Types</option>
              <option value="City">City</option>
              <option value="Suburban">Suburban</option>
              <option value="Town">Town</option>
              <option value="Rural">Rural</option>
            </select>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              aria-label="Sort members"
              className="border border-pebble rounded-input px-3 py-2 text-sm bg-white"
            >
              <option value="match_score">Best Match</option>
              <option value="name">Name (A-Z)</option>
              <option value="joined">Recently Joined</option>
            </select>
          </div>
        </div>

        {/* Results count */}
        <p className="text-sm text-stone mb-4">
          {totalCount} member{totalCount !== 1 ? "s" : ""} found
        </p>

        {/* Member grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="bg-sand animate-pulse rounded-card h-48"
              />
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {members.map((m) => (
                <div
                  key={m.id}
                  className="bg-chalk rounded-card border border-pebble shadow-card p-4 hover:shadow-card-hover transition-shadow"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-10 h-10 rounded-full bg-deep text-white font-display font-bold text-sm flex items-center justify-center">
                        {m.first_name[0]}
                        {m.last_name[0]}
                      </div>
                      <div>
                        <p className="font-display text-abyss font-bold text-sm">
                          {m.first_name} {m.last_name}
                        </p>
                        {m.district && (
                          <p className="text-stone text-xs">
                            {m.district.name}, {m.district.state}
                          </p>
                        )}
                      </div>
                    </div>
                    {m.is_featured && (
                      <span className="bg-amber text-white text-xs font-bold px-2 py-0.5 rounded-badge">
                        Featured
                      </span>
                    )}
                  </div>

                  {/* Bio excerpt */}
                  {m.bio_excerpt && (
                    <p className="text-obsidian text-xs mb-3 line-clamp-2">
                      {m.bio_excerpt}
                    </p>
                  )}

                  {/* Problem selections */}
                  {m.problem_selections.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {m.problem_selections.map((ps, i) => (
                        <span
                          key={i}
                          className="bg-sand text-obsidian text-xs px-2 py-0.5 rounded-badge"
                        >
                          {ps.title}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between mt-auto pt-2 border-t border-pebble">
                    <div className="flex items-center gap-2">
                      <span className="text-current font-bold text-sm">
                        {m.match_score}%
                      </span>
                      <span className="text-stone text-xs">match</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {connectionBadge(m.connection_status)}
                      {m.connection_status === "NONE" && (
                        <button
                          onClick={() => handleConnect(m.id)}
                          className="bg-current text-white text-xs font-bold px-3 py-1 rounded-input hover:bg-deep transition-colors"
                        >
                          Connect
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {members.length === 0 && !loading && (
              <p className="text-stone text-center py-8">
                No members match your filters.
              </p>
            )}

            {/* Pagination */}
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => fetchMembers(page - 1)}
                disabled={page <= 1}
                className="bg-chalk border border-pebble text-obsidian text-sm px-4 py-2 rounded-input hover:bg-sand disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-stone">Page {page}</span>
              <button
                onClick={() => fetchMembers(page + 1)}
                disabled={!hasMore}
                className="bg-chalk border border-pebble text-obsidian text-sm px-4 py-2 rounded-input hover:bg-sand disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
