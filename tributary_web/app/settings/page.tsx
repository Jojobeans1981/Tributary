"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import NavHeader from "@/app/components/NavHeader";

/* ---------- types ---------- */

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
  email_preference: string;
}

interface ProblemStatement {
  id: number;
  title: string;
  description: string;
  category: string;
}

interface Selection {
  id: string;
  problem_statement: ProblemStatement;
  elaboration_text: string;
  selected_at: string;
}

interface District {
  id: string;
  nces_id: string;
  name: string;
  state: string;
  locale_type: string;
  enrollment: number;
}

/* ---------- component ---------- */

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);

  // Problem selections
  const [selections, setSelections] = useState<Selection[]>([]);
  const [allProblems, setAllProblems] = useState<ProblemStatement[]>([]);
  const [showAddPicker, setShowAddPicker] = useState(false);
  const [editingElaboration, setEditingElaboration] = useState<string | null>(null);
  const [elaborationValue, setElaborationValue] = useState("");
  const [saving, setSaving] = useState(false);

  // District
  const [editingDistrict, setEditingDistrict] = useState(false);
  const [districtQuery, setDistrictQuery] = useState("");
  const [districtResults, setDistrictResults] = useState<District[]>([]);
  const [districtLoading, setDistrictLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Email preference
  const [emailPref, setEmailPref] = useState("");
  const [emailPrefSaving, setEmailPrefSaving] = useState(false);

  // Toast
  const [toast, setToast] = useState("");
  const [toastType, setToastType] = useState<"success" | "error">("success");

  const showToast = (msg: string, type: "success" | "error" = "success") => {
    setToast(msg);
    setToastType(type);
    setTimeout(() => setToast(""), 3000);
  };

  /* ---------- initial fetch ---------- */

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    Promise.all([
      apiFetch<UserData>("/api/users/me/"),
      apiFetch<Selection[]>("/api/users/me/problem-selections/"),
      apiFetch<ProblemStatement[]>("/api/problems/"),
    ]).then(([userRes, selRes, probRes]) => {
      setLoading(false);
      if (!userRes.success) {
        router.replace("/login");
        return;
      }
      setUser(userRes.data!);
      setEmailPref(userRes.data!.email_preference);
      if (selRes.success && selRes.data) setSelections(selRes.data);
      if (probRes.success && probRes.data) setAllProblems(probRes.data);
    });
  }, [router]);

  /* ---------- district search ---------- */

  useEffect(() => {
    if (districtQuery.length < 2) {
      setDistrictResults([]);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setDistrictLoading(true);
      const res = await apiFetch<District[]>(
        `/api/districts/?search=${encodeURIComponent(districtQuery)}`
      );
      setDistrictLoading(false);
      if (res.success && res.data) setDistrictResults(res.data);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [districtQuery]);

  /* ---------- handlers ---------- */

  const handleDeleteSelection = async (selId: string) => {
    setSaving(true);
    const res = await apiFetch(`/api/users/me/problem-selections/${selId}/`, {
      method: "DELETE",
    });
    setSaving(false);
    if (res.success) {
      setSelections((prev) => prev.filter((s) => s.id !== selId));
      showToast("Selection removed. Match scores will update shortly.");
    } else {
      showToast("Failed to remove selection.", "error");
    }
  };

  const handleSaveElaboration = async (selId: string) => {
    setSaving(true);
    const res = await apiFetch(`/api/users/me/problem-selections/${selId}/`, {
      method: "PATCH",
      body: JSON.stringify({ elaboration_text: elaborationValue }),
    });
    setSaving(false);
    if (res.success) {
      setSelections((prev) =>
        prev.map((s) =>
          s.id === selId ? { ...s, elaboration_text: elaborationValue } : s
        )
      );
      setEditingElaboration(null);
      showToast("Elaboration updated.");
    } else {
      showToast("Failed to update elaboration.", "error");
    }
  };

  const handleAddSelection = async (problemId: number) => {
    setSaving(true);
    const res = await apiFetch<Selection>("/api/users/me/problem-selections/", {
      method: "POST",
      body: JSON.stringify({ problem_statement_id: problemId, elaboration_text: "" }),
    });
    setSaving(false);
    if (res.success && res.data) {
      setSelections((prev) => [...prev, res.data!]);
      setShowAddPicker(false);
      showToast("Problem statement added. Match scores will update shortly.");
    } else {
      showToast(
        typeof res.error?.message === "string"
          ? res.error.message
          : "Failed to add selection.",
        "error"
      );
    }
  };

  const handleDistrictSelect = async (district: District) => {
    setSaving(true);
    const res = await apiFetch("/api/users/me/", {
      method: "PATCH",
      body: JSON.stringify({ district: district.nces_id }),
    });
    setSaving(false);
    if (res.success) {
      setUser((prev) =>
        prev ? { ...prev, district: { ...district } } : prev
      );
      setEditingDistrict(false);
      setDistrictQuery("");
      setDistrictResults([]);
      showToast("District updated. Match scores will update shortly.");
    } else {
      showToast("Failed to update district.", "error");
    }
  };

  const handleEmailPrefChange = async (value: string) => {
    setEmailPref(value);
    setEmailPrefSaving(true);
    const res = await apiFetch("/api/users/me/", {
      method: "PATCH",
      body: JSON.stringify({ email_preference: value }),
    });
    setEmailPrefSaving(false);
    if (res.success) {
      showToast("Email preference updated.");
    } else {
      showToast("Failed to update email preference.", "error");
    }
  };

  /* ---------- derived ---------- */

  const selectedProblemIds = new Set(selections.map((s) => s.problem_statement.id));
  const availableProblems = allProblems.filter((p) => !selectedProblemIds.has(p.id));

  /* ---------- render ---------- */

  if (loading || !user) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-3xl mx-auto p-6 space-y-4">
          <div className="bg-sand animate-pulse rounded-card h-10 w-48" />
          <div className="bg-sand animate-pulse rounded-card h-40" />
          <div className="bg-sand animate-pulse rounded-card h-40" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={user} />
      <main className="max-w-3xl mx-auto p-6">
        <h1 className="font-display text-abyss text-3xl font-bold mb-6">
          Settings
        </h1>

        {/* Toast */}
        {toast && (
          <div
            className={`text-sm px-4 py-2 rounded-card mb-4 border ${
              toastType === "success"
                ? "bg-go/10 text-go border-go"
                : "bg-stop-light text-stop border-stop"
            }`}
          >
            {toast}
          </div>
        )}

        {/* ========== Problem Selections ========== */}
        <section
          className="bg-chalk rounded-card shadow-card p-6 border border-pebble mb-6"
          aria-label="Problem statements"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-abyss text-xl font-bold">
              Problem Statements
            </h2>
            <span className="text-stone text-sm">{selections.length} of 3</span>
          </div>
          <p className="text-stone text-sm mb-4">
            These determine who you&rsquo;re matched with. Changing them will recalculate your match scores.
          </p>

          {selections.length === 0 && (
            <p className="text-stone text-sm italic mb-4">No problem statements selected.</p>
          )}

          <div className="space-y-3">
            {selections.map((sel) => (
              <div
                key={sel.id}
                className="bg-mist rounded-input p-4 border border-pebble"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <span className="bg-foam text-current text-xs font-bold px-2 py-0.5 rounded-badge">
                      {sel.problem_statement.category}
                    </span>
                    <h3 className="font-display text-abyss text-sm font-bold mt-1">
                      {sel.problem_statement.title}
                    </h3>
                    <p className="text-stone text-xs mt-1">
                      {sel.problem_statement.description}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteSelection(sel.id)}
                    disabled={saving}
                    className="text-stop text-xs font-bold px-2 py-1 rounded-input hover:bg-stop-light transition-colors shrink-0"
                    aria-label={`Remove ${sel.problem_statement.title}`}
                  >
                    Remove
                  </button>
                </div>

                {/* Elaboration */}
                {editingElaboration === sel.id ? (
                  <div className="mt-3">
                    <textarea
                      value={elaborationValue}
                      onChange={(e) => setElaborationValue(e.target.value)}
                      maxLength={280}
                      rows={2}
                      className="w-full bg-chalk border border-pebble rounded-input px-3 py-2 text-sm text-obsidian focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20"
                      placeholder="Add context about your experience with this challenge..."
                    />
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-stone text-xs">
                        {elaborationValue.length}/280
                      </span>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setEditingElaboration(null)}
                          className="text-stone text-xs hover:underline"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSaveElaboration(sel.id)}
                          disabled={saving}
                          className="bg-current text-white text-xs font-bold px-3 py-1 rounded-input hover:bg-deep transition-colors disabled:opacity-50"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="mt-2">
                    {sel.elaboration_text ? (
                      <p className="text-obsidian text-xs italic">
                        &ldquo;{sel.elaboration_text}&rdquo;
                      </p>
                    ) : null}
                    <button
                      onClick={() => {
                        setEditingElaboration(sel.id);
                        setElaborationValue(sel.elaboration_text || "");
                      }}
                      className="text-current text-xs mt-1 hover:underline"
                    >
                      {sel.elaboration_text ? "Edit context" : "Add context"}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Add new selection */}
          {selections.length < 3 && (
            <div className="mt-4">
              {showAddPicker ? (
                <div className="bg-mist rounded-input p-4 border border-current">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-display text-abyss text-sm font-bold">
                      Add a problem statement
                    </h3>
                    <button
                      onClick={() => setShowAddPicker(false)}
                      className="text-stone text-xs hover:underline"
                    >
                      Cancel
                    </button>
                  </div>
                  {availableProblems.length === 0 ? (
                    <p className="text-stone text-sm">No more problem statements available.</p>
                  ) : (
                    <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto">
                      {availableProblems.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => handleAddSelection(p.id)}
                          disabled={saving}
                          className="text-left bg-chalk rounded-input p-3 border border-pebble hover:border-current hover:shadow-card-hover transition-all disabled:opacity-50"
                        >
                          <span className="bg-foam text-current text-xs font-bold px-2 py-0.5 rounded-badge">
                            {p.category}
                          </span>
                          <h4 className="text-abyss text-sm font-bold mt-1">
                            {p.title}
                          </h4>
                          <p className="text-stone text-xs mt-0.5 line-clamp-2">
                            {p.description}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <button
                  onClick={() => setShowAddPicker(true)}
                  className="w-full border-2 border-dashed border-pebble rounded-input p-3 text-current text-sm font-bold hover:border-current hover:bg-foam/30 transition-colors"
                >
                  + Add problem statement ({3 - selections.length} remaining)
                </button>
              )}
            </div>
          )}
        </section>

        {/* ========== District ========== */}
        <section
          className="bg-chalk rounded-card shadow-card p-6 border border-pebble mb-6"
          aria-label="District"
        >
          <h2 className="font-display text-abyss text-xl font-bold mb-4">
            District
          </h2>
          <p className="text-stone text-sm mb-4">
            Your district determines the demographic side of your match score.
          </p>

          {editingDistrict ? (
            <div>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search districts..."
                  value={districtQuery}
                  onChange={(e) => setDistrictQuery(e.target.value)}
                  className="w-full bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20"
                  autoFocus
                />
                {districtLoading && (
                  <div className="absolute right-3 top-2.5 text-stone text-sm">...</div>
                )}
                {districtResults.length > 0 && (
                  <div className="absolute w-full mt-1 bg-chalk border border-pebble rounded-input shadow-card max-h-60 overflow-y-auto z-10">
                    {districtResults.map((d) => (
                      <button
                        key={d.id}
                        onClick={() => handleDistrictSelect(d)}
                        className="w-full text-left px-3 py-2 hover:bg-sand transition-colors text-sm"
                      >
                        <span className="font-semibold text-obsidian">{d.name}</span>
                        <span className="text-stone ml-2">
                          {d.state} &middot; {d.locale_type} &middot;{" "}
                          {d.enrollment.toLocaleString()} students
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => {
                  setEditingDistrict(false);
                  setDistrictQuery("");
                  setDistrictResults([]);
                }}
                className="text-stone text-xs mt-2 hover:underline"
              >
                Cancel
              </button>
            </div>
          ) : user.district ? (
            <div className="flex items-center justify-between bg-mist rounded-input p-4 border border-pebble">
              <div>
                <p className="font-display text-abyss font-bold">
                  {user.district.name}
                </p>
                <p className="text-stone text-sm">
                  {user.district.state} &middot; {user.district.locale_type} &middot;{" "}
                  {user.district.enrollment.toLocaleString()} students
                </p>
              </div>
              <button
                onClick={() => setEditingDistrict(true)}
                className="text-current text-sm font-bold hover:underline shrink-0"
              >
                Change
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditingDistrict(true)}
              className="w-full border-2 border-dashed border-pebble rounded-input p-3 text-current text-sm font-bold hover:border-current hover:bg-foam/30 transition-colors"
            >
              + Select your district
            </button>
          )}
        </section>

        {/* ========== Email Preferences ========== */}
        <section
          className="bg-chalk rounded-card shadow-card p-6 border border-pebble mb-6"
          aria-label="Email preferences"
        >
          <h2 className="font-display text-abyss text-xl font-bold mb-4">
            Email Notifications
          </h2>
          <div className="space-y-2">
            {[
              { value: "IMMEDIATE", label: "Immediate", desc: "Get notified right away" },
              { value: "DAILY_DIGEST", label: "Daily Digest", desc: "One summary email per day" },
              { value: "OFF", label: "Off", desc: "No email notifications" },
            ].map((opt) => (
              <label
                key={opt.value}
                className={`flex items-center gap-3 p-3 rounded-input border cursor-pointer transition-colors ${
                  emailPref === opt.value
                    ? "border-current bg-foam"
                    : "border-pebble bg-mist hover:border-stone"
                }`}
              >
                <input
                  type="radio"
                  name="email_preference"
                  value={opt.value}
                  checked={emailPref === opt.value}
                  onChange={(e) => handleEmailPrefChange(e.target.value)}
                  disabled={emailPrefSaving}
                  className="accent-current"
                />
                <div>
                  <p className="text-obsidian text-sm font-bold">{opt.label}</p>
                  <p className="text-stone text-xs">{opt.desc}</p>
                </div>
              </label>
            ))}
          </div>
        </section>

        {/* ========== Account Info ========== */}
        <section
          className="bg-chalk rounded-card shadow-card p-6 border border-pebble"
          aria-label="Account information"
        >
          <h2 className="font-display text-abyss text-xl font-bold mb-4">
            Account
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-stone">Email</span>
              <span className="text-obsidian">{user.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-stone">Name</span>
              <span className="text-obsidian">
                {user.first_name} {user.last_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-stone">Role</span>
              <span className="text-obsidian">{user.role}</span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-pebble">
            <Link
              href={`/profile/${user.id}`}
              className="text-current text-sm font-bold hover:underline"
            >
              Edit profile &rarr;
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
