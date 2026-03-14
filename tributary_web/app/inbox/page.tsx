"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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

interface ConvoItem {
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
  conversation_id: string;
  sender_id: string;
  sender_name: string;
  body: string;
  attachment_url: string | null;
  attachment_type: string | null;
  sent_at: string;
  is_deleted: boolean;
  system_message: boolean;
}

/* ---------- component ---------- */

export default function InboxPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeData | null>(null);
  const [convos, setConvos] = useState<ConvoItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mobileShowThread, setMobileShowThread] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  /* auth + initial fetch */
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/login"); return; }

    apiFetch<MeData>("/api/users/me/").then((res) => {
      if (res.success && res.data) setMe(res.data);
    });

    apiFetch<ConvoItem[]>("/api/conversations/").then((res) => {
      if (res.success && res.data) setConvos(res.data);
      setLoading(false);
    });
  }, [router]);

  /* open a conversation */
  const openConvo = useCallback(
    async (id: string) => {
      setActiveId(id);
      setMobileShowThread(true);

      const res = await apiFetch<MessageItem[]>(
        `/api/conversations/${id}/messages/`
      );
      if (res.success && res.data) {
        setMessages(res.data.reverse());
      }

      // mark read
      await apiFetch(`/api/conversations/${id}/read/`, { method: "PATCH" });

      // update unread in sidebar
      setConvos((prev) =>
        prev.map((c) => (c.id === id ? { ...c, unread_count: 0 } : c))
      );
    },
    []
  );

  /* WebSocket for active conversation */
  useEffect(() => {
    if (!activeId) return;
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const wsBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
      .replace(/^http/, "ws");
    const ws = new WebSocket(
      `${wsBase}/ws/chat/${activeId}/?token=${token}`
    );
    wsRef.current = ws;

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "chat.message") {
        const incoming: MessageItem = {
          id: data.message_id,
          conversation_id: activeId,
          sender_id: data.sender_id,
          sender_name: data.sender_name,
          body: data.body,
          attachment_url: data.attachment_url,
          attachment_type: data.attachment_type,
          sent_at: data.sent_at,
          is_deleted: false,
          system_message: false,
        };
        setMessages((prev) => [...prev, incoming]);
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [activeId]);

  /* scroll to bottom on new messages */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* send message */
  const handleSend = async () => {
    if (!activeId || !body.trim()) return;
    setSending(true);

    // Send via REST (WebSocket will echo it back)
    await apiFetch(`/api/conversations/${activeId}/messages/`, {
      method: "POST",
      body: JSON.stringify({ body: body.trim() }),
    });

    setBody("");
    setSending(false);

    // update sidebar preview
    setConvos((prev) =>
      prev.map((c) =>
        c.id === activeId
          ? { ...c, last_message_preview: body.trim().slice(0, 60) }
          : c
      )
    );
  };

  /* file upload */
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeId) return;

    const formData = new FormData();
    formData.append("file", file);

    const token = localStorage.getItem("access_token");
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const res = await fetch(`${API_BASE}/api/upload/`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      await apiFetch(`/api/conversations/${activeId}/messages/`, {
        method: "POST",
        body: JSON.stringify({
          body: `Shared a file: ${file.name}`,
          attachment_url: data.url,
          attachment_type: data.attachment_type,
        }),
      });
    }
    e.target.value = "";
  };

  /* other participant name */
  const otherName = (convo: ConvoItem) => {
    if (!me) return "";
    const other = convo.participants.find((p) => p.user_id !== me.id);
    return other?.full_name || "Unknown";
  };

  /* loading skeleton */
  if (loading) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-5xl mx-auto p-6 space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-sand animate-pulse rounded-card h-16" />
          ))}
        </div>
      </div>
    );
  }

  const activeConvo = convos.find((c) => c.id === activeId);

  return (
    <div className="bg-mist min-h-screen flex flex-col">
      <NavHeader user={me} />

      <div className="flex flex-1 overflow-hidden" style={{ height: "calc(100vh - 64px)" }}>
        {/* Conversation list */}
        <aside
          className={`${
            mobileShowThread ? "hidden md:flex" : "flex"
          } flex-col w-full md:w-80 shrink-0 bg-chalk border-r border-pebble overflow-y-auto`}
        >
          <div className="p-4 border-b border-pebble">
            <h1 className="font-display text-abyss text-lg font-bold">Inbox</h1>
          </div>

          {convos.length === 0 ? (
            <div className="p-4 text-stone text-sm text-center">
              No conversations yet. Connect with a match to start chatting.
            </div>
          ) : (
            convos.map((c) => (
              <button
                key={c.id}
                onClick={() => openConvo(c.id)}
                className={`w-full text-left p-4 border-b border-pebble hover:bg-sand transition-colors ${
                  activeId === c.id ? "bg-foam/30" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-display text-abyss font-bold text-sm truncate">
                    {otherName(c)}
                  </span>
                  {c.unread_count > 0 && (
                    <span className="bg-current text-white text-xs font-bold px-2 py-0.5 rounded-full">
                      {c.unread_count}
                    </span>
                  )}
                </div>
                {c.last_message_preview && (
                  <p className="text-stone text-xs mt-1 truncate">
                    {c.last_message_preview}
                  </p>
                )}
                {c.is_staff_initiated && (
                  <span className="text-amber text-xs font-bold">Staff</span>
                )}
              </button>
            ))
          )}
        </aside>

        {/* Message thread */}
        <main
          className={`${
            mobileShowThread ? "flex" : "hidden md:flex"
          } flex-col flex-1`}
        >
          {!activeConvo ? (
            <div className="flex-1 flex items-center justify-center text-stone text-sm">
              Select a conversation
            </div>
          ) : (
            <>
              {/* Thread header */}
              <div className="p-4 border-b border-pebble bg-chalk flex items-center gap-3">
                <button
                  className="md:hidden text-obsidian"
                  onClick={() => setMobileShowThread(false)}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <h2 className="font-display text-abyss font-bold text-sm">
                  {otherName(activeConvo)}
                </h2>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.map((msg) => {
                  const isMe = me && msg.sender_id === me.id;
                  return (
                    <div
                      key={msg.id}
                      className={`flex ${isMe ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[75%] rounded-card px-3 py-2 ${
                          msg.system_message
                            ? "bg-sand text-stone text-xs italic text-center w-full max-w-full"
                            : isMe
                            ? "bg-current text-white"
                            : "bg-chalk border border-pebble text-obsidian"
                        }`}
                      >
                        {!isMe && !msg.system_message && (
                          <p className="text-xs font-bold text-deep mb-1">
                            {msg.sender_name}
                          </p>
                        )}
                        <p className="text-sm whitespace-pre-wrap">{msg.body}</p>
                        {msg.attachment_url && (
                          <a
                            href={msg.attachment_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`text-xs underline mt-1 block ${
                              isMe ? "text-foam" : "text-current"
                            }`}
                          >
                            View attachment ({msg.attachment_type})
                          </a>
                        )}
                        <p
                          className={`text-xs mt-1 ${
                            isMe ? "text-foam/70" : "text-stone"
                          }`}
                        >
                          {new Date(msg.sent_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={bottomRef} />
              </div>

              {/* Compose */}
              <div className="p-3 border-t border-pebble bg-chalk flex items-center gap-2">
                <label className="shrink-0 cursor-pointer text-stone hover:text-current transition-colors">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.jpg,.jpeg,.png,.docx"
                    onChange={handleUpload}
                  />
                </label>
                <input
                  type="text"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Type a message..."
                  maxLength={5000}
                  className="flex-1 border border-pebble rounded-input px-3 py-2 text-sm focus:outline-none focus:border-current"
                />
                <button
                  onClick={handleSend}
                  disabled={sending || !body.trim()}
                  className="bg-current text-white text-sm font-bold px-4 py-2 rounded-input hover:bg-deep disabled:bg-pebble transition-colors"
                >
                  Send
                </button>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
