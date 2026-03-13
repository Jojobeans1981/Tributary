"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

interface District {
  id: string;
  nces_id: string;
  name: string;
  state: string;
  locale_type: string;
  enrollment: number;
}

export default function DistrictSelectPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<District[]>([]);
  const [selected, setSelected] = useState<District | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      const res = await apiFetch<District[]>(
        `/api/districts/?search=${encodeURIComponent(query)}`
      );
      setLoading(false);
      if (res.success && res.data) {
        setResults(res.data);
      }
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const handleSelect = (district: District) => {
    setSelected(district);
    setQuery(district.name);
    setResults([]);
  };

  const handleContinue = async () => {
    if (!selected) return;
    setSaving(true);
    setError("");

    const res = await apiFetch<unknown>("/api/users/me/", {
      method: "PATCH",
      body: JSON.stringify({ district: selected.nces_id }),
    });

    setSaving(false);

    if (!res.success) {
      setError(
        typeof res.error?.message === "string"
          ? res.error.message
          : "Failed to save district."
      );
      return;
    }

    router.push("/dashboard");
  };

  return (
    <div className="bg-mist min-h-screen flex items-center justify-center px-4">
      <div className="bg-chalk rounded-card shadow-card p-8 w-full max-w-md border border-pebble">
        <h1 className="font-display text-abyss text-2xl font-bold mb-2">
          Select Your District
        </h1>
        <p className="text-stone text-sm mb-6">
          Start typing to search districts by name.
        </p>

        {error && (
          <div className="bg-stop-light border border-stop text-stop rounded-input px-3 py-2 text-sm mb-4">
            {error}
          </div>
        )}

        <div className="relative mb-6">
          <input
            type="text"
            placeholder="Search districts..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelected(null);
            }}
            className="w-full bg-sand border border-pebble rounded-input px-3 py-2 text-obsidian placeholder:text-stone focus:outline-none focus:border-current focus:ring-2 focus:ring-current/20"
          />
          {loading && (
            <div className="absolute right-3 top-2.5 text-stone text-sm">
              ...
            </div>
          )}
          {results.length > 0 && !selected && (
            <div className="absolute w-full mt-1 bg-chalk border border-pebble rounded-input shadow-card max-h-60 overflow-y-auto z-10">
              {results.map((d) => (
                <button
                  key={d.id}
                  onClick={() => handleSelect(d)}
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

        {selected && (
          <div className="bg-foam rounded-card p-3 mb-6 border border-current/20">
            <p className="font-semibold text-abyss">{selected.name}</p>
            <p className="text-sm text-deep">
              {selected.state} &middot; {selected.locale_type} &middot;{" "}
              {selected.enrollment.toLocaleString()} students
            </p>
          </div>
        )}

        <button
          onClick={handleContinue}
          disabled={!selected || saving}
          className="w-full bg-current text-white font-bold py-3 px-6 rounded-input hover:bg-surface active:bg-deep disabled:bg-pebble disabled:text-stone transition-colors duration-150"
        >
          {saving ? "Saving..." : "Continue"}
        </button>
      </div>
    </div>
  );
}
