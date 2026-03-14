"use client";

import { useState, useEffect } from "react";
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

interface Channel {
  id: number;
  title: string;
  category: string;
  member_count: number;
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

interface ChannelMembersResponse {
  channel: { id: number; title: string; category: string };
  members: MemberItem[];
}

/* ---------- component ---------- */

export default function ChannelsPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeData | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);

  /* channel detail */
  const [activeChannel, setActiveChannel] = useState<{
    id: number;
    title: string;
    category: string;
  } | null>(null);
  const [channelMembers, setChannelMembers] = useState<MemberItem[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);

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

  /* fetch channels */
  useEffect(() => {
    if (!me) return;
    apiFetch<Channel[]>("/api/channels/").then((res) => {
      if (res.success && res.data) setChannels(res.data);
      setLoading(false);
    });
  }, [me]);

  /* open channel */
  const openChannel = async (ch: Channel) => {
    setActiveChannel({ id: ch.id, title: ch.title, category: ch.category });
    setMembersLoading(true);
    const res = await apiFetch<ChannelMembersResponse>(
      `/api/channels/${ch.id}/members/`
    );
    if (res.success && res.data) {
      setChannelMembers(res.data.members);
    }
    setMembersLoading(false);
  };

  /* connect */
  const handleConnect = async (memberId: string) => {
    const res = await apiFetch("/api/connections/", {
      method: "POST",
      body: JSON.stringify({ recipient_id: memberId }),
    });
    if (res.success) {
      setChannelMembers((prev) =>
        prev.map((m) =>
          m.id === memberId ? { ...m, connection_status: "PENDING_SENT" } : m
        )
      );
    }
  };

  if (!me) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-5xl mx-auto p-6 space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-sand animate-pulse rounded-card h-20" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />

      <main id="main-content" className="max-w-5xl mx-auto p-6" aria-label="Channels">
        <h1 className="font-display text-abyss text-2xl font-bold mb-6">
          Channels
        </h1>

        {/* Back button when viewing members */}
        {activeChannel && (
          <button
            onClick={() => {
              setActiveChannel(null);
              setChannelMembers([]);
            }}
            className="text-current text-sm font-bold mb-4 hover:underline"
          >
            &larr; Back to Channels
          </button>
        )}

        {/* Channel list */}
        {!activeChannel && (
          <>
            {loading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="bg-sand animate-pulse rounded-card h-20"
                  />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {channels.map((ch) => (
                  <button
                    key={ch.id}
                    onClick={() => openChannel(ch)}
                    className="bg-chalk rounded-card border border-pebble shadow-card p-4 text-left hover:shadow-card-hover transition-shadow"
                  >
                    <h2 className="font-display text-abyss font-bold">
                      {ch.title}
                    </h2>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="bg-deep text-white text-xs px-2 py-0.5 rounded-badge">
                        {ch.category}
                      </span>
                      <span className="text-stone text-sm">
                        {ch.member_count} member
                        {ch.member_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </button>
                ))}
                {channels.length === 0 && (
                  <p className="text-stone text-sm col-span-2">
                    No channels available.
                  </p>
                )}
              </div>
            )}
          </>
        )}

        {/* Channel members view */}
        {activeChannel && (
          <div>
            <div className="mb-4">
              <h2 className="font-display text-abyss text-xl font-bold">
                {activeChannel.title}
              </h2>
              <span className="bg-deep text-white text-xs px-2 py-0.5 rounded-badge">
                {activeChannel.category}
              </span>
            </div>

            {membersLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                  <div
                    key={i}
                    className="bg-sand animate-pulse rounded-card h-40"
                  />
                ))}
              </div>
            ) : (
              <>
                <p className="text-sm text-stone mb-4">
                  {channelMembers.length} member
                  {channelMembers.length !== 1 ? "s" : ""} in this channel
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {channelMembers.map((m) => (
                    <div
                      key={m.id}
                      className="bg-chalk rounded-card border border-pebble shadow-card p-4"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-9 h-9 rounded-full bg-deep text-white font-display font-bold text-xs flex items-center justify-center">
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
                        {m.is_featured && (
                          <span className="bg-amber text-white text-xs font-bold px-1.5 py-0.5 rounded-badge ml-auto">
                            Featured
                          </span>
                        )}
                      </div>

                      {m.bio_excerpt && (
                        <p className="text-obsidian text-xs mb-2 line-clamp-2">
                          {m.bio_excerpt}
                        </p>
                      )}

                      <div className="flex items-center justify-between pt-2 border-t border-pebble">
                        <span className="text-current font-bold text-sm">
                          {m.match_score}% match
                        </span>
                        {m.connection_status === "NONE" ? (
                          <button
                            onClick={() => handleConnect(m.id)}
                            className="bg-current text-white text-xs font-bold px-3 py-1 rounded-input hover:bg-deep transition-colors"
                          >
                            Connect
                          </button>
                        ) : m.connection_status === "ACCEPTED" ? (
                          <span className="bg-go-light text-go text-xs font-bold px-2 py-0.5 rounded-badge">
                            Connected
                          </span>
                        ) : m.connection_status === "PENDING_SENT" ? (
                          <span className="bg-amber-light text-amber text-xs font-bold px-2 py-0.5 rounded-badge">
                            Pending
                          </span>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
                {channelMembers.length === 0 && (
                  <p className="text-stone text-center py-8">
                    No other members in this channel yet.
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
