"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearTokens } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

interface User {
  id: string;
  first_name: string;
  last_name: string;
  role?: string;
}

export default function NavHeader({ user }: { user: User | null }) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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

  /* Close dropdown on Escape */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setMenuOpen(false);
      setMobileOpen(false);
    }
  };

  return (
    <header
      className="bg-abyss h-16 sticky top-0 z-50 flex items-center justify-between px-6"
      role="banner"
      onKeyDown={handleKeyDown}
    >
      <Link
        href="/dashboard"
        className="flex items-center gap-2 font-display text-current text-xl font-bold"
        aria-label="Tributary home"
      >
        {/* Tributary logo — converging streams */}
        <svg
          width="32"
          height="32"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="shrink-0"
        >
          {/* Left tributary stream */}
          <path
            d="M10 8C14 20 18 28 32 40C32 40 32 48 32 58"
            stroke="#0E7C8B"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Right tributary stream */}
          <path
            d="M54 8C50 20 46 28 32 40"
            stroke="#0E7C8B"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Small left branch */}
          <path
            d="M4 22C12 26 20 32 28 36"
            stroke="#12A8BC"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          {/* Small right branch */}
          <path
            d="M60 22C52 26 44 32 36 36"
            stroke="#12A8BC"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          {/* Water drop at confluence */}
          <circle cx="32" cy="42" r="3.5" fill="#C8EEF2" />
          {/* Flow lines below confluence */}
          <path
            d="M30 50C30 52 31 55 32 58"
            stroke="#C8EEF2"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <path
            d="M34 50C34 52 33 55 32 58"
            stroke="#C8EEF2"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        TRIBUTARY
        {/* Mirrored logo — horizontally flipped */}
        <svg
          width="32"
          height="32"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="shrink-0"
          style={{ transform: "scaleX(-1)" }}
        >
          {/* Left tributary stream */}
          <path
            d="M10 8C14 20 18 28 32 40C32 40 32 48 32 58"
            stroke="#0E7C8B"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Right tributary stream */}
          <path
            d="M54 8C50 20 46 28 32 40"
            stroke="#0E7C8B"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Small left branch */}
          <path
            d="M4 22C12 26 20 32 28 36"
            stroke="#12A8BC"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          {/* Small right branch */}
          <path
            d="M60 22C52 26 44 32 36 36"
            stroke="#12A8BC"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          {/* Water drop at confluence */}
          <circle cx="32" cy="42" r="3.5" fill="#C8EEF2" />
          {/* Flow lines below confluence */}
          <path
            d="M30 50C30 52 31 55 32 58"
            stroke="#C8EEF2"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <path
            d="M34 50C34 52 33 55 32 58"
            stroke="#C8EEF2"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </Link>

      {/* Desktop nav */}
      <nav
        className="hidden md:flex items-center gap-4"
        aria-label="Main navigation"
      >
        <Link
          href="/community"
          className="text-foam text-sm hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-foam focus:ring-offset-2 focus:ring-offset-abyss rounded px-1"
        >
          Community
        </Link>
        <Link
          href="/channels"
          className="text-foam text-sm hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-foam focus:ring-offset-2 focus:ring-offset-abyss rounded px-1"
        >
          Channels
        </Link>
        <Link
          href="/matches"
          className="text-foam text-sm hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-foam focus:ring-offset-2 focus:ring-offset-abyss rounded px-1"
        >
          Matches
        </Link>
        <Link
          href="/inbox"
          className="text-foam text-sm hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-foam focus:ring-offset-2 focus:ring-offset-abyss rounded px-1"
        >
          Inbox
        </Link>
        {(user.role === "UPSTREAM_STAFF" || user.role === "PLATFORM_ADMIN") && (
          <Link
            href="/staff"
            className="text-amber text-sm font-bold hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-foam focus:ring-offset-2 focus:ring-offset-abyss rounded px-1"
          >
            Admin
          </Link>
        )}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            aria-expanded={menuOpen}
            aria-haspopup="true"
            aria-label="User menu"
            className="w-9 h-9 rounded-full bg-foam text-abyss font-display font-bold text-sm flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-foam focus:ring-offset-2 focus:ring-offset-abyss"
          >
            {initials}
          </button>
          {menuOpen && (
            <div
              className="absolute right-0 mt-2 w-40 bg-chalk rounded-card shadow-card border border-pebble py-1 z-50"
              role="menu"
            >
              <Link
                href={`/profile/${user.id}`}
                className="block px-4 py-2 text-sm text-obsidian hover:bg-sand focus:bg-sand focus:outline-none"
                onClick={() => setMenuOpen(false)}
                role="menuitem"
              >
                Profile
              </Link>
              <Link
                href="/settings"
                className="block px-4 py-2 text-sm text-obsidian hover:bg-sand focus:bg-sand focus:outline-none"
                onClick={() => setMenuOpen(false)}
                role="menuitem"
              >
                Settings
              </Link>
              <button
                onClick={handleSignOut}
                className="block w-full text-left px-4 py-2 text-sm text-obsidian hover:bg-sand focus:bg-sand focus:outline-none"
                role="menuitem"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Mobile hamburger */}
      <button
        className="md:hidden text-white focus:outline-none focus:ring-2 focus:ring-foam rounded"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-expanded={mobileOpen}
        aria-label="Open navigation menu"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
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
        <div
          className="fixed inset-0 z-50 md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
        >
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute right-0 top-0 h-full w-64 bg-abyss p-6">
            <button
              className="text-white mb-8 focus:outline-none focus:ring-2 focus:ring-foam rounded"
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation menu"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            <nav className="flex flex-col gap-4" aria-label="Mobile navigation">
              <Link
                href="/community"
                className="text-foam text-lg focus:outline-none focus:ring-2 focus:ring-foam rounded px-1"
                onClick={() => setMobileOpen(false)}
              >
                Community
              </Link>
              <Link
                href="/channels"
                className="text-foam text-lg focus:outline-none focus:ring-2 focus:ring-foam rounded px-1"
                onClick={() => setMobileOpen(false)}
              >
                Channels
              </Link>
              <Link
                href="/matches"
                className="text-foam text-lg focus:outline-none focus:ring-2 focus:ring-foam rounded px-1"
                onClick={() => setMobileOpen(false)}
              >
                Matches
              </Link>
              <Link
                href="/inbox"
                className="text-foam text-lg focus:outline-none focus:ring-2 focus:ring-foam rounded px-1"
                onClick={() => setMobileOpen(false)}
              >
                Inbox
              </Link>
              {(user.role === "UPSTREAM_STAFF" || user.role === "PLATFORM_ADMIN") && (
                <Link
                  href="/staff"
                  className="text-amber text-lg font-bold focus:outline-none focus:ring-2 focus:ring-foam rounded px-1"
                  onClick={() => setMobileOpen(false)}
                >
                  Admin
                </Link>
              )}
              <Link
                href={`/profile/${user.id}`}
                className="text-foam text-lg focus:outline-none focus:ring-2 focus:ring-foam rounded px-1"
                onClick={() => setMobileOpen(false)}
              >
                Profile
              </Link>
              <Link
                href="/settings"
                className="text-foam text-lg focus:outline-none focus:ring-2 focus:ring-foam rounded px-1"
                onClick={() => setMobileOpen(false)}
              >
                Settings
              </Link>
              <button
                onClick={handleSignOut}
                className="text-foam text-lg text-left focus:outline-none focus:ring-2 focus:ring-foam rounded px-1"
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
