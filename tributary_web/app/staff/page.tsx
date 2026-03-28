"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import NavHeader from "@/app/components/NavHeader";

/* ---------- types ---------- */

interface MeData {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
}

interface Participant {
  user_id: string;
  full_name: string;
}

interface StaffConvo {
  id: string;
  conversation_type: string;
  is_staff_initiated: boolean;
  created_at: string;
  last_message_preview: string | null;
  unread_count: number;
  participants: Participant[];
}

interface MessageItem {
  id: string;
  sender_id: string;
  sender_name: string;
  body: string;
  sent_at: string;
  is_deleted: boolean;
  system_message: boolean;
}

interface AnalyticsSummary {
  total_members: number;
  messages_sent: number;
  match_acceptance_rate: number;
  avg_feedback_rating: number | null;
}

interface FeaturedMember {
  id: string;
  user_id: string;
  user_name: string;
  featured_by: string;
  featured_from: string;
  featured_until: string | null;
  note: string;
}

interface CommunityMember {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
  bio_excerpt: string;
  district: { name: string; state: string; locale_type: string } | null;
  match_score: number;
  connection_status: string;
  is_featured: boolean;
}

type Tab = "overview" | "conversations" | "users" | "featured";

/* ---------- component ---------- */

export default function StaffDashboardPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [feedback, setFeedback] = useState("");
  const [feedbackType, setFeedbackType] = useState<"success" | "error">("success");

  const showFeedback = (msg: string, type: "success" | "error" = "success") => {
    setFeedback(msg);
    setFeedbackType(type);
    setTimeout(() => setFeedback(""), 4000);
  };

  /* auth check */
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/login"); return; }

    apiFetch<MeData>("/api/users/me/").then((res) => {
      if (res.success && res.data) {
        if (res.data.role !== "UPSTREAM_STAFF" && res.data.role !== "PLATFORM_ADMIN") {
          router.replace("/dashboard");
          return;
        }
        setMe(res.data);
        setLoading(false);
      }
    });
  }, [router]);

  if (loading || !me) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-7xl mx-auto p-6 space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-sand animate-pulse rounded-card h-24" />
          ))}
        </div>
      </div>
    );
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "conversations", label: "Conversations" },
    { key: "users", label: "Users" },
    { key: "featured", label: "Featured" },
  ];

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />

      <main className="max-w-7xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-display text-abyss text-2xl font-bold">
            Staff Dashboard
          </h1>
          <div className="flex gap-2">
            <Link
              href="/staff/analytics"
              className="bg-deep text-white text-sm font-bold px-3 py-2 rounded-input hover:bg-abyss transition-colors"
            >
              Analytics
            </Link>
            <Link
              href="/staff/taxonomy"
              className="bg-deep text-white text-sm font-bold px-3 py-2 rounded-input hover:bg-abyss transition-colors"
            >
              Taxonomy
            </Link>
          </div>
        </div>

        {/* Feedback toast */}
        {feedback && (
          <div className={`text-sm px-4 py-2 rounded-card mb-4 border flex justify-between items-center ${
            feedbackType === "success"
              ? "bg-go/10 text-go border-go"
              : "bg-stop-light text-stop border-stop"
          }`}>
            <span>{feedback}</span>
            <button onClick={() => setFeedback("")} className="font-bold ml-4">&times;</button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-pebble">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`px-4 py-2 text-sm font-bold transition-colors border-b-2 -mb-px ${
                activeTab === t.key
                  ? "text-current border-current"
                  : "text-stone border-transparent hover:text-obsidian"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {activeTab === "overview" && <OverviewTab />}
        {activeTab === "conversations" && <ConversationsTab showFeedback={showFeedback} />}
        {activeTab === "users" && <UsersTab showFeedback={showFeedback} />}
        {activeTab === "featured" && <FeaturedTab showFeedback={showFeedback} />}
      </main>
    </div>
  );
}

/* ========== OVERVIEW TAB ========== */

function OverviewTab() {
  const [stats, setStats] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    apiFetch<any>("/api/staff/analytics/").then((res) => {
      if (res.success && res.data) {
        setStats({
          total_members: res.data.total_members,
          messages_sent: res.data.messages_sent,
          match_acceptance_rate: res.data.match_acceptance_rate,
          avg_feedback_rating: res.data.avg_feedback_rating,
        });
      }
    });
  }, []);

  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-sand animate-pulse rounded-card h-24" />
        ))}
      </div>
    );
  }

  const cards = [
    { label: "Total Members", value: stats.total_members.toLocaleString(), color: "text-current" },
    { label: "Messages Sent", value: stats.messages_sent.toLocaleString(), color: "text-deep" },
    { label: "Match Accept Rate", value: `${stats.match_acceptance_rate}%`, color: "text-go" },
    { label: "Avg Feedback", value: stats.avg_feedback_rating ? `${stats.avg_feedback_rating}/5` : "N/A", color: "text-amber" },
  ];

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {cards.map((c) => (
          <div key={c.label} className="bg-chalk rounded-card shadow-card p-4 border border-pebble">
            <p className="text-stone text-xs uppercase tracking-wide">{c.label}</p>
            <p className={`font-display text-2xl font-bold mt-1 ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Link
          href="/staff/analytics"
          className="bg-chalk rounded-card shadow-card p-6 border border-pebble hover:shadow-card-hover transition-shadow"
        >
          <h3 className="font-display text-abyss font-bold mb-1">Analytics Dashboard</h3>
          <p className="text-stone text-sm">Growth charts, message volume, problem distribution, top district pairs.</p>
        </Link>
        <Link
          href="/staff/taxonomy"
          className="bg-chalk rounded-card shadow-card p-6 border border-pebble hover:shadow-card-hover transition-shadow"
        >
          <h3 className="font-display text-abyss font-bold mb-1">Problem Taxonomy</h3>
          <p className="text-stone text-sm">Manage problem statements — add, edit, retire, track member counts.</p>
        </Link>
      </div>
    </div>
  );
}

/* ========== CONVERSATIONS TAB ========== */

function ConversationsTab({ showFeedback }: { showFeedback: (msg: string, type?: "success" | "error") => void }) {
  const [convos, setConvos] = useState<StaffConvo[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [staffFilter, setStaffFilter] = useState(false);
  const [loadingConvos, setLoadingConvos] = useState(true);

  // Modals
  const [showDM, setShowDM] = useState(false);
  const [dmRecipient, setDmRecipient] = useState("");
  const [dmBody, setDmBody] = useState("");
  const [showBroadcast, setShowBroadcast] = useState(false);
  const [bcRecipients, setBcRecipients] = useState("");
  const [bcBody, setBcBody] = useState("");

  const fetchConvos = useCallback(() => {
    setLoadingConvos(true);
    const params = staffFilter ? "?staff_initiated=true" : "";
    apiFetch<StaffConvo[]>(`/api/staff/conversations/${params}`).then((res) => {
      if (res.success && res.data) setConvos(res.data);
      setLoadingConvos(false);
    });
  }, [staffFilter]);

  useEffect(() => { fetchConvos(); }, [fetchConvos]);

  const openConvo = async (id: string) => {
    setActiveId(id);
    const res = await apiFetch<MessageItem[]>(`/api/conversations/${id}/messages/`);
    if (res.success && res.data) setMessages(res.data.reverse());
  };

  const handleJoin = async (id: string) => {
    const res = await apiFetch(`/api/staff/conversations/${id}/join/`, { method: "POST" });
    if (res.success) {
      showFeedback("Joined conversation.");
      openConvo(id);
    }
  };

  const handleDeleteMsg = async (msgId: string) => {
    const res = await apiFetch(`/api/staff/messages/${msgId}/`, { method: "DELETE" });
    if (res.success) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId ? { ...m, is_deleted: true, body: "[This message was removed by a moderator]" } : m
        )
      );
    }
  };

  const handleSendDM = async () => {
    const res = await apiFetch("/api/staff/messages/", {
      method: "POST",
      body: JSON.stringify({ recipient_id: dmRecipient.trim(), body: dmBody }),
    });
    if (res.success) {
      showFeedback("Direct message sent.");
      setShowDM(false);
      setDmRecipient("");
      setDmBody("");
      fetchConvos();
    } else {
      showFeedback("Failed to send DM.", "error");
    }
  };

  const handleBroadcast = async () => {
    const ids = bcRecipients.split(",").map((s) => s.trim()).filter(Boolean);
    const res = await apiFetch("/api/staff/broadcast/", {
      method: "POST",
      body: JSON.stringify({ body: bcBody, recipient_ids: ids }),
    });
    if (res.success) {
      showFeedback("Broadcast sent.");
      setShowBroadcast(false);
      setBcRecipients("");
      setBcBody("");
      fetchConvos();
    } else {
      showFeedback("Broadcast failed (check rate limit).", "error");
    }
  };

  const participantNames = (c: StaffConvo) => c.participants.map((p) => p.full_name).join(", ");

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <label className="flex items-center gap-2 text-sm text-obsidian">
          <input
            type="checkbox"
            checked={staffFilter}
            onChange={() => setStaffFilter(!staffFilter)}
            className="accent-current"
          />
          Staff-initiated only
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => setShowDM(true)}
            className="bg-current text-white text-sm font-bold px-3 py-2 rounded-input hover:bg-deep transition-colors"
          >
            Direct Message
          </button>
          <button
            onClick={() => setShowBroadcast(true)}
            className="bg-deep text-white text-sm font-bold px-3 py-2 rounded-input hover:bg-abyss transition-colors"
          >
            Broadcast
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Conversation list */}
        <div>
          <h2 className="font-display text-abyss font-bold mb-3">Conversations</h2>
          {loadingConvos ? (
            <div className="space-y-2">{[...Array(3)].map((_, i) => (
              <div key={i} className="bg-sand animate-pulse rounded-card h-16" />
            ))}</div>
          ) : (
            <div className="space-y-2 max-h-[60vh] overflow-y-auto">
              {convos.map((c) => (
                <div
                  key={c.id}
                  className={`bg-chalk rounded-card border border-pebble p-3 cursor-pointer hover:shadow-card transition-shadow ${
                    activeId === c.id ? "ring-2 ring-current" : ""
                  }`}
                  onClick={() => openConvo(c.id)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-display text-abyss text-sm font-bold truncate">
                      {participantNames(c)}
                    </span>
                    {c.is_staff_initiated && (
                      <span className="bg-amber text-white text-xs px-2 py-0.5 rounded-badge">Staff</span>
                    )}
                  </div>
                  {c.last_message_preview && (
                    <p className="text-stone text-xs mt-1 truncate">{c.last_message_preview}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-stone text-xs">{new Date(c.created_at).toLocaleDateString()}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleJoin(c.id); }}
                      className="text-current text-xs font-bold hover:underline"
                    >
                      Join
                    </button>
                  </div>
                </div>
              ))}
              {convos.length === 0 && <p className="text-stone text-sm">No conversations found.</p>}
            </div>
          )}
        </div>

        {/* Message thread */}
        <div>
          <h2 className="font-display text-abyss font-bold mb-3">Messages</h2>
          {!activeId ? (
            <p className="text-stone text-sm">Select a conversation to view messages.</p>
          ) : (
            <div className="bg-chalk rounded-card border border-pebble">
              <div className="max-h-[50vh] overflow-y-auto p-4 space-y-2">
                {messages.map((msg) => (
                  <div key={msg.id} className="group">
                    <div className={`rounded-card px-3 py-2 ${
                      msg.system_message
                        ? "bg-sand text-stone text-xs italic"
                        : msg.is_deleted
                        ? "bg-stop-light border border-stop text-stone"
                        : "bg-white border border-pebble"
                    }`}>
                      <div className="flex justify-between items-start">
                        <p className="text-xs font-bold text-deep">{msg.sender_name}</p>
                        {!msg.is_deleted && !msg.system_message && (
                          <button
                            onClick={() => handleDeleteMsg(msg.id)}
                            className="hidden group-hover:block text-stop text-xs font-bold hover:underline"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                      <p className="text-sm text-obsidian whitespace-pre-wrap">{msg.body}</p>
                      <p className="text-xs text-stone mt-1">{new Date(msg.sent_at).toLocaleString()}</p>
                    </div>
                  </div>
                ))}
                {messages.length === 0 && <p className="text-stone text-sm text-center py-4">No messages.</p>}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* DM Modal */}
      {showDM && (
        <Modal title="Direct Message" onClose={() => setShowDM(false)}>
          <label className="block text-sm text-obsidian mb-1">Recipient User ID</label>
          <input
            value={dmRecipient}
            onChange={(e) => setDmRecipient(e.target.value)}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3 bg-sand"
            placeholder="UUID"
          />
          <label className="block text-sm text-obsidian mb-1">Message</label>
          <textarea
            value={dmBody}
            onChange={(e) => setDmBody(e.target.value)}
            maxLength={5000}
            rows={4}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3 bg-sand"
          />
          <button
            onClick={handleSendDM}
            disabled={!dmRecipient.trim() || !dmBody.trim()}
            className="bg-current text-white text-sm font-bold px-4 py-2 rounded-input hover:bg-deep disabled:bg-pebble transition-colors"
          >
            Send
          </button>
        </Modal>
      )}

      {/* Broadcast Modal */}
      {showBroadcast && (
        <Modal title="Broadcast" onClose={() => setShowBroadcast(false)}>
          <label className="block text-sm text-obsidian mb-1">Recipient IDs (comma-separated)</label>
          <textarea
            value={bcRecipients}
            onChange={(e) => setBcRecipients(e.target.value)}
            rows={2}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3 bg-sand"
            placeholder="uuid1, uuid2, ..."
          />
          <label className="block text-sm text-obsidian mb-1">Message</label>
          <textarea
            value={bcBody}
            onChange={(e) => setBcBody(e.target.value)}
            maxLength={5000}
            rows={4}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3 bg-sand"
          />
          <button
            onClick={handleBroadcast}
            disabled={!bcRecipients.trim() || !bcBody.trim()}
            className="bg-deep text-white text-sm font-bold px-4 py-2 rounded-input hover:bg-abyss disabled:bg-pebble transition-colors"
          >
            Send Broadcast
          </button>
        </Modal>
      )}
    </div>
  );
}

/* ========== USERS TAB ========== */

function UsersTab({ showFeedback }: { showFeedback: (msg: string, type?: "success" | "error") => void }) {
  const [members, setMembers] = useState<CommunityMember[]>([]);
  const [search, setSearch] = useState("");
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [showSuspend, setShowSuspend] = useState(false);
  const [suspendTarget, setSuspendTarget] = useState<{ id: string; name: string } | null>(null);
  const [suspendNote, setSuspendNote] = useState("");

  const fetchMembers = useCallback((q: string) => {
    setLoadingMembers(true);
    const params = q ? `?search=${encodeURIComponent(q)}&sort=name` : "?sort=name";
    apiFetch<{ results: CommunityMember[] }>(`/api/community/${params}`).then((res) => {
      if (res.success && res.data) setMembers(res.data.results);
      setLoadingMembers(false);
    });
  }, []);

  useEffect(() => { fetchMembers(""); }, [fetchMembers]);

  useEffect(() => {
    const t = setTimeout(() => fetchMembers(search), 300);
    return () => clearTimeout(t);
  }, [search, fetchMembers]);

  const handleSuspend = async () => {
    if (!suspendTarget) return;
    const res = await apiFetch(`/api/staff/users/${suspendTarget.id}/suspend/`, {
      method: "POST",
      body: JSON.stringify({ note: suspendNote }),
    });
    if (res.success) {
      showFeedback(`${suspendTarget.name} suspended.`);
      setMembers((prev) => prev.filter((m) => m.id !== suspendTarget.id));
      setShowSuspend(false);
      setSuspendTarget(null);
      setSuspendNote("");
    } else {
      showFeedback("Failed to suspend user.", "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or district..."
          className="w-full max-w-md bg-sand border border-pebble rounded-input px-3 py-2 text-sm text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20"
        />
      </div>

      {loadingMembers ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => (
          <div key={i} className="bg-sand animate-pulse rounded-card h-16" />
        ))}</div>
      ) : (
        <div className="bg-chalk rounded-card shadow-card border border-pebble overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-sand text-left">
                <th className="px-4 py-3 font-display text-abyss font-bold">Name</th>
                <th className="px-4 py-3 font-display text-abyss font-bold hidden md:table-cell">District</th>
                <th className="px-4 py-3 font-display text-abyss font-bold hidden md:table-cell">Role</th>
                <th className="px-4 py-3 font-display text-abyss font-bold text-center">Featured</th>
                <th className="px-4 py-3 font-display text-abyss font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id} className="border-t border-pebble hover:bg-mist transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/profile/${m.id}`} className="text-current font-bold hover:underline">
                      {m.first_name} {m.last_name}
                    </Link>
                    <p className="text-stone text-xs truncate max-w-[200px]">{m.bio_excerpt}</p>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell text-stone">
                    {m.district ? `${m.district.name}, ${m.district.state}` : "—"}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className="bg-deep text-white text-xs px-2 py-0.5 rounded-badge">{m.role}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {m.is_featured && (
                      <span className="bg-amber text-white text-xs px-2 py-0.5 rounded-badge">Featured</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-2 justify-end">
                      <Link
                        href={`/profile/${m.id}`}
                        className="text-current text-xs font-bold hover:underline"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => {
                          setSuspendTarget({ id: m.id, name: `${m.first_name} ${m.last_name}` });
                          setShowSuspend(true);
                        }}
                        className="text-stop text-xs font-bold hover:underline"
                      >
                        Suspend
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {members.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-stone">
                    No members found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Suspend Modal */}
      {showSuspend && suspendTarget && (
        <Modal title="Suspend User" onClose={() => { setShowSuspend(false); setSuspendTarget(null); }}>
          <p className="text-sm text-obsidian mb-3">
            Are you sure you want to suspend <strong>{suspendTarget.name}</strong>?
            This will deactivate their account.
          </p>
          <label className="block text-sm text-obsidian mb-1">Note (optional)</label>
          <textarea
            value={suspendNote}
            onChange={(e) => setSuspendNote(e.target.value)}
            rows={2}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3 bg-sand"
          />
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => { setShowSuspend(false); setSuspendTarget(null); }}
              className="text-stone text-sm font-bold px-4 py-2 hover:underline"
            >
              Cancel
            </button>
            <button
              onClick={handleSuspend}
              className="bg-stop text-white text-sm font-bold px-4 py-2 rounded-input hover:opacity-90 transition-colors"
            >
              Suspend
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

/* ========== FEATURED TAB ========== */

function FeaturedTab({ showFeedback }: { showFeedback: (msg: string, type?: "success" | "error") => void }) {
  const [featured, setFeatured] = useState<FeaturedMember[]>([]);
  const [loadingFeatured, setLoadingFeatured] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [addUserId, setAddUserId] = useState("");
  const [addNote, setAddNote] = useState("");

  const fetchFeatured = useCallback(() => {
    setLoadingFeatured(true);
    apiFetch<FeaturedMember[]>("/api/staff/featured/").then((res) => {
      if (res.success && res.data) setFeatured(res.data);
      setLoadingFeatured(false);
    });
  }, []);

  useEffect(() => { fetchFeatured(); }, [fetchFeatured]);

  const handleAdd = async () => {
    const res = await apiFetch("/api/staff/featured/", {
      method: "POST",
      body: JSON.stringify({ user_id: addUserId.trim(), note: addNote }),
    });
    if (res.success) {
      showFeedback("Member featured.");
      setShowAdd(false);
      setAddUserId("");
      setAddNote("");
      fetchFeatured();
    } else {
      const msg = typeof res.error?.message === "string" ? res.error.message : "Failed to feature member.";
      showFeedback(msg, "error");
    }
  };

  const handleRemove = async (id: string, name: string) => {
    const res = await apiFetch(`/api/staff/featured/${id}/`, { method: "DELETE" });
    if (res.success) {
      showFeedback(`${name} removed from featured.`);
      setFeatured((prev) => prev.filter((f) => f.id !== id));
    } else {
      showFeedback("Failed to remove.", "error");
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-stone text-sm">
            Featured members appear highlighted in the community directory. Maximum 5 active.
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          disabled={featured.length >= 5}
          className="bg-current text-white text-sm font-bold px-3 py-2 rounded-input hover:bg-deep disabled:bg-pebble transition-colors"
        >
          + Feature Member
        </button>
      </div>

      {loadingFeatured ? (
        <div className="space-y-2">{[...Array(3)].map((_, i) => (
          <div key={i} className="bg-sand animate-pulse rounded-card h-16" />
        ))}</div>
      ) : featured.length === 0 ? (
        <div className="bg-chalk rounded-card shadow-card p-8 border border-pebble text-center">
          <p className="text-stone">No featured members yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {featured.map((f) => (
            <div
              key={f.id}
              className="bg-chalk rounded-card shadow-card p-4 border border-amber flex items-center justify-between"
            >
              <div>
                <Link
                  href={`/profile/${f.user_id}`}
                  className="font-display text-abyss font-bold hover:underline"
                >
                  {f.user_name}
                </Link>
                <p className="text-stone text-xs mt-0.5">
                  Featured by {f.featured_by} &middot; Since{" "}
                  {new Date(f.featured_from).toLocaleDateString()}
                  {f.featured_until && ` &middot; Until ${new Date(f.featured_until).toLocaleDateString()}`}
                </p>
                {f.note && <p className="text-obsidian text-xs mt-1 italic">&ldquo;{f.note}&rdquo;</p>}
              </div>
              <button
                onClick={() => handleRemove(f.id, f.user_name)}
                className="text-stop text-xs font-bold px-2 py-1 hover:underline shrink-0"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add Featured Modal */}
      {showAdd && (
        <Modal title="Feature a Member" onClose={() => setShowAdd(false)}>
          <label className="block text-sm text-obsidian mb-1">User ID</label>
          <input
            value={addUserId}
            onChange={(e) => setAddUserId(e.target.value)}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3 bg-sand"
            placeholder="UUID"
          />
          <label className="block text-sm text-obsidian mb-1">Note (optional)</label>
          <textarea
            value={addNote}
            onChange={(e) => setAddNote(e.target.value)}
            rows={2}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3 bg-sand"
          />
          <button
            onClick={handleAdd}
            disabled={!addUserId.trim()}
            className="bg-current text-white text-sm font-bold px-4 py-2 rounded-input hover:bg-deep disabled:bg-pebble transition-colors"
          >
            Feature Member
          </button>
        </Modal>
      )}
    </div>
  );
}

/* ---------- reusable modal ---------- */

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div className="relative bg-chalk rounded-card shadow-card border border-pebble p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display text-abyss font-bold">{title}</h3>
          <button onClick={onClose} aria-label="Close dialog" className="text-stone text-xl font-bold">
            &times;
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
