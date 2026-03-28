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

/* ---------- component ---------- */

export default function StaffDashboardPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeData | null>(null);
  const [convos, setConvos] = useState<StaffConvo[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);

  /* modals / forms */
  const [showDM, setShowDM] = useState(false);
  const [dmRecipient, setDmRecipient] = useState("");
  const [dmBody, setDmBody] = useState("");
  const [showBroadcast, setShowBroadcast] = useState(false);
  const [bcRecipients, setBcRecipients] = useState("");
  const [bcBody, setBcBody] = useState("");
  const [showSuspend, setShowSuspend] = useState(false);
  const [suspendId, setSuspendId] = useState("");
  const [suspendNote, setSuspendNote] = useState("");
  const [feedback, setFeedback] = useState("");
  const [staffFilter, setStaffFilter] = useState(false);

  /* auth check — restrict to staff roles */
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
      }
    });
  }, [router]);

  /* fetch conversations */
  useEffect(() => {
    if (!me) return;
    const params = staffFilter ? "?staff_initiated=true" : "";
    apiFetch<StaffConvo[]>(`/api/staff/conversations/${params}`).then((res) => {
      if (res.success && res.data) setConvos(res.data);
      setLoading(false);
    });
  }, [me, staffFilter]);

  /* open a conversation */
  const openConvo = async (id: string) => {
    setActiveId(id);
    const res = await apiFetch<MessageItem[]>(
      `/api/conversations/${id}/messages/`
    );
    if (res.success && res.data) {
      setMessages(res.data.reverse());
    }
  };

  /* staff join */
  const handleJoin = async (id: string) => {
    const res = await apiFetch(`/api/staff/conversations/${id}/join/`, {
      method: "POST",
    });
    if (res.success) {
      setFeedback("Joined conversation.");
      openConvo(id);
    }
  };

  /* delete message */
  const handleDeleteMsg = async (msgId: string) => {
    const res = await apiFetch(`/api/staff/messages/${msgId}/`, {
      method: "DELETE",
    });
    if (res.success) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? { ...m, is_deleted: true, body: "[This message was removed by a moderator]" }
            : m
        )
      );
    }
  };

  /* send DM */
  const handleSendDM = async () => {
    const res = await apiFetch("/api/staff/messages/", {
      method: "POST",
      body: JSON.stringify({ recipient_id: dmRecipient.trim(), body: dmBody }),
    });
    if (res.success) {
      setFeedback("Direct message sent.");
      setShowDM(false);
      setDmRecipient("");
      setDmBody("");
    } else {
      setFeedback("Failed to send DM.");
    }
  };

  /* broadcast */
  const handleBroadcast = async () => {
    const ids = bcRecipients.split(",").map((s) => s.trim()).filter(Boolean);
    const res = await apiFetch("/api/staff/broadcast/", {
      method: "POST",
      body: JSON.stringify({ body: bcBody, recipient_ids: ids }),
    });
    if (res.success) {
      setFeedback("Broadcast sent.");
      setShowBroadcast(false);
      setBcRecipients("");
      setBcBody("");
    } else {
      setFeedback("Broadcast failed (check rate limit).");
    }
  };

  /* suspend */
  const handleSuspend = async () => {
    const res = await apiFetch(`/api/staff/users/${suspendId.trim()}/suspend/`, {
      method: "POST",
      body: JSON.stringify({ note: suspendNote }),
    });
    if (res.success) {
      setFeedback("User suspended.");
      setShowSuspend(false);
      setSuspendId("");
      setSuspendNote("");
    } else {
      setFeedback("Failed to suspend user.");
    }
  };

  /* participant names */
  const participantNames = (c: StaffConvo) =>
    c.participants.map((p) => p.full_name).join(", ");

  if (loading) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-6xl mx-auto p-6 space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-sand animate-pulse rounded-card h-16" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />

      <main id="main-content" className="max-w-6xl mx-auto p-6" aria-label="Staff dashboard">
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-display text-abyss text-2xl font-bold">
            Staff Dashboard
          </h1>
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
            <button
              onClick={() => setShowSuspend(true)}
              className="bg-stop text-white text-sm font-bold px-3 py-2 rounded-input hover:opacity-90 transition-colors"
            >
              Suspend User
            </button>
          </div>
        </div>

        {/* Feedback toast */}
        {feedback && (
          <div className="bg-go-light border border-go text-go rounded-card p-3 mb-4 flex justify-between items-center">
            <span className="text-sm">{feedback}</span>
            <button onClick={() => setFeedback("")} className="text-go font-bold">
              &times;
            </button>
          </div>
        )}

        {/* Filter */}
        <div className="mb-4">
          <label className="flex items-center gap-2 text-sm text-obsidian">
            <input
              type="checkbox"
              checked={staffFilter}
              onChange={() => { setStaffFilter(!staffFilter); setLoading(true); }}
              className="accent-current"
            />
            Staff-initiated only
          </label>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Conversation list */}
          <div>
            <h2 className="font-display text-abyss font-bold mb-3">Conversations</h2>
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
                      <span className="bg-amber text-white text-xs px-2 py-0.5 rounded-badge">
                        Staff
                      </span>
                    )}
                  </div>
                  {c.last_message_preview && (
                    <p className="text-stone text-xs mt-1 truncate">
                      {c.last_message_preview}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-stone text-xs">
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleJoin(c.id); }}
                      className="text-current text-xs font-bold hover:underline"
                    >
                      Join
                    </button>
                  </div>
                </div>
              ))}
              {convos.length === 0 && (
                <p className="text-stone text-sm">No conversations found.</p>
              )}
            </div>
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
                      <div
                        className={`rounded-card px-3 py-2 ${
                          msg.system_message
                            ? "bg-sand text-stone text-xs italic"
                            : msg.is_deleted
                            ? "bg-stop-light border border-stop text-stone"
                            : "bg-white border border-pebble"
                        }`}
                      >
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
                        <p className="text-xs text-stone mt-1">
                          {new Date(msg.sent_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                  {messages.length === 0 && (
                    <p className="text-stone text-sm text-center py-4">No messages.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* DM Modal */}
      {showDM && (
        <Modal title="Direct Message" onClose={() => setShowDM(false)}>
          <label className="block text-sm text-obsidian mb-1">Recipient User ID</label>
          <input
            value={dmRecipient}
            onChange={(e) => setDmRecipient(e.target.value)}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
            placeholder="UUID"
          />
          <label className="block text-sm text-obsidian mb-1">Message</label>
          <textarea
            value={dmBody}
            onChange={(e) => setDmBody(e.target.value)}
            maxLength={5000}
            rows={4}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
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
          <label className="block text-sm text-obsidian mb-1">
            Recipient IDs (comma-separated)
          </label>
          <textarea
            value={bcRecipients}
            onChange={(e) => setBcRecipients(e.target.value)}
            rows={2}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
            placeholder="uuid1, uuid2, ..."
          />
          <label className="block text-sm text-obsidian mb-1">Message</label>
          <textarea
            value={bcBody}
            onChange={(e) => setBcBody(e.target.value)}
            maxLength={5000}
            rows={4}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
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

      {/* Suspend Modal */}
      {showSuspend && (
        <Modal title="Suspend User" onClose={() => setShowSuspend(false)}>
          <label className="block text-sm text-obsidian mb-1">User ID</label>
          <input
            value={suspendId}
            onChange={(e) => setSuspendId(e.target.value)}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
            placeholder="UUID"
          />
          <label className="block text-sm text-obsidian mb-1">Note (optional)</label>
          <textarea
            value={suspendNote}
            onChange={(e) => setSuspendNote(e.target.value)}
            rows={2}
            className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
          />
          <button
            onClick={handleSuspend}
            disabled={!suspendId.trim()}
            className="bg-stop text-white text-sm font-bold px-4 py-2 rounded-input hover:opacity-90 disabled:bg-pebble transition-colors"
          >
            Suspend
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
