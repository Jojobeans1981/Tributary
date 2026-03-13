"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

interface ProblemStatement {
  id: number;
  title: string;
  description: string;
  category: string;
}

interface Selection {
  problem_statement_id: number;
  elaboration_text: string;
}

export default function ProblemsPage() {
  const router = useRouter();
  const [problems, setProblems] = useState<ProblemStatement[]>([]);
  const [selected, setSelected] = useState<Map<number, string>>(new Map());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    // Check if user already has selections → redirect to dashboard
    Promise.all([
      apiFetch<ProblemStatement[]>("/api/problems/"),
      apiFetch<any[]>("/api/users/me/problem-selections/"),
    ]).then(([problemsRes, selectionsRes]) => {
      setLoading(false);
      if (selectionsRes.success && selectionsRes.data && selectionsRes.data.length > 0) {
        router.replace("/dashboard");
        return;
      }
      if (problemsRes.success && problemsRes.data) {
        setProblems(problemsRes.data);
      }
    });
  }, [router]);

  const toggleSelect = (id: number) => {
    const next = new Map(selected);
    if (next.has(id)) {
      next.delete(id);
    } else {
      if (next.size >= 3) {
        setToast("You can select a maximum of 3 problem statements.");
        setTimeout(() => setToast(""), 3000);
        return;
      }
      next.set(id, "");
    }
    setSelected(next);
  };

  const updateElaboration = (id: number, text: string) => {
    const next = new Map(selected);
    next.set(id, text);
    setSelected(next);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    const selections: Selection[] = [];
    selected.forEach((text, id) => {
      selections.push({ problem_statement_id: id, elaboration_text: text });
    });

    for (const sel of selections) {
      const res = await apiFetch("/api/users/me/problem-selections/", {
        method: "POST",
        body: JSON.stringify(sel),
      });
      if (!res.success) {
        setToast(res.error?.message || "Failed to save selection.");
        setSubmitting(false);
        return;
      }
    }

    router.push("/dashboard");
  };

  if (loading) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-5xl mx-auto p-6 space-y-4">
          <div className="bg-sand animate-pulse rounded-card h-10 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-sand animate-pulse rounded-card h-40" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <div className="bg-abyss h-16 flex items-center px-6">
        <span className="font-display text-current text-xl font-bold">TRIBUTARY</span>
      </div>

      <main className="max-w-5xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-display text-abyss text-3xl font-bold">
              What challenges are you facing?
            </h1>
            <p className="text-stone text-sm mt-1">
              Select up to 3 problem statements that resonate with your work.
            </p>
          </div>
          <span className="text-current font-display font-bold text-lg">
            {selected.size} of 3 selected
          </span>
        </div>

        {/* Toast */}
        {toast && (
          <div className="bg-stop-light text-stop text-sm px-4 py-2 rounded-card mb-4 border border-stop">
            {toast}
          </div>
        )}

        {/* Problem cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {problems.map((p) => {
            const isSelected = selected.has(p.id);
            return (
              <div key={p.id} className="flex flex-col">
                <button
                  onClick={() => toggleSelect(p.id)}
                  className={`relative text-left rounded-card p-4 border transition-colors ${
                    isSelected
                      ? "border-current border-2 bg-foam"
                      : "bg-chalk border-pebble hover:shadow-card-hover"
                  }`}
                >
                  {/* Checkmark badge */}
                  {isSelected && (
                    <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-current flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}

                  <span className="bg-foam text-current text-xs font-bold px-2 py-1 rounded-badge">
                    {p.category}
                  </span>
                  <h3 className="font-display text-abyss text-sm font-bold mt-2 pr-6">
                    {p.title}
                  </h3>
                  <p className="text-stone text-xs mt-1 line-clamp-3">
                    {p.description}
                  </p>
                </button>

                {/* Elaboration textarea */}
                {isSelected && (
                  <div className="mt-2">
                    <textarea
                      value={selected.get(p.id) || ""}
                      onChange={(e) => updateElaboration(p.id, e.target.value)}
                      maxLength={280}
                      placeholder="Add context (optional)..."
                      className="w-full bg-chalk border border-pebble rounded-input p-2 text-sm text-obsidian resize-none h-20 focus:outline-none focus:border-current"
                    />
                    <p className="text-stone text-xs text-right">
                      {(selected.get(p.id) || "").length}/280
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Submit */}
        <div className="flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={selected.size < 1 || submitting}
            className="bg-current text-white font-bold px-8 py-3 rounded-input disabled:opacity-50 disabled:cursor-not-allowed hover:bg-deep transition-colors"
          >
            {submitting ? "Saving..." : "Continue"}
          </button>
        </div>
      </main>
    </div>
  );
}
