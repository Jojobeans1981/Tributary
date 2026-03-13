"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearTokens } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

interface User {
  id: string;
  first_name: string;
  last_name: string;
}

export default function NavHeader({ user }: { user: User | null }) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  if (!user) return null;

  const initials =
    `${user.first_name?.[0] || ""}${user.last_name?.[0] || ""}`.toUpperCase();

  const handleSignOut = async () => {
    const refresh = localStorage.getItem("refresh_token");
    if (refresh) {
      await apiFetch("/api/auth/logout/", {
        method: "POST",
        body: JSON.stringify({ refresh }),
      });
    }
    clearTokens();
    router.push("/login");
  };

  return (
    <header className="bg-abyss h-16 sticky top-0 z-50 flex items-center justify-between px-6">
      <Link
        href="/dashboard"
        className="font-display text-current text-xl font-bold"
      >
        TRIBUTARY
      </Link>

      {/* Desktop nav */}
      <div className="hidden md:flex items-center gap-4">
        <Link href="/matches" className="text-foam text-sm hover:text-white transition-colors">
          Matches
        </Link>
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="w-9 h-9 rounded-full bg-foam text-abyss font-display font-bold text-sm flex items-center justify-center"
          >
            {initials}
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-40 bg-chalk rounded-card shadow-card border border-pebble py-1 z-50">
              <Link
                href={`/profile/${user.id}`}
                className="block px-4 py-2 text-sm text-obsidian hover:bg-sand"
                onClick={() => setMenuOpen(false)}
              >
                Profile
              </Link>
              <button
                onClick={handleSignOut}
                className="block w-full text-left px-4 py-2 text-sm text-obsidian hover:bg-sand"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Mobile hamburger */}
      <button
        className="md:hidden text-white"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute right-0 top-0 h-full w-64 bg-abyss p-6">
            <button
              className="text-white mb-8"
              onClick={() => setMobileOpen(false)}
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            <nav className="flex flex-col gap-4">
              <Link
                href="/matches"
                className="text-foam text-lg"
                onClick={() => setMobileOpen(false)}
              >
                Matches
              </Link>
              <Link
                href={`/profile/${user.id}`}
                className="text-foam text-lg"
                onClick={() => setMobileOpen(false)}
              >
                Profile
              </Link>
              <button
                onClick={handleSignOut}
                className="text-foam text-lg text-left"
              >
                Sign out
              </button>
            </nav>
          </div>
        </div>
      )}
    </header>
  );
}
