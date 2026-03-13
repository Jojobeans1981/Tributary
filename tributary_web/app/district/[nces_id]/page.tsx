"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import NavHeader from "@/app/components/NavHeader";

interface Member {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
}

interface DistrictData {
  id: string;
  nces_id: string;
  name: string;
  state: string;
  locale_type: string;
  enrollment: number;
  frl_pct: string;
  ell_pct: string;
  data_vintage: string;
  members: Member[];
}

interface MeData {
  id: string;
  first_name: string;
  last_name: string;
}

export default function DistrictPage() {
  const router = useRouter();
  const params = useParams();
  const nces_id = params.nces_id as string;
  const [district, setDistrict] = useState<DistrictData | null>(null);
  const [me, setMe] = useState<MeData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    Promise.all([
      apiFetch<DistrictData>(`/api/districts/${nces_id}/`),
      apiFetch<MeData>("/api/users/me/"),
    ]).then(([districtRes, meRes]) => {
      setLoading(false);
      if (districtRes.success && districtRes.data) {
        setDistrict(districtRes.data);
      }
      if (meRes.success && meRes.data) {
        setMe(meRes.data);
      }
    });
  }, [nces_id, router]);

  if (loading || !district) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-3xl mx-auto p-6 space-y-4">
          <div className="bg-sand animate-pulse rounded-card h-10 w-72" />
          <div className="bg-sand animate-pulse rounded-card h-24" />
          <div className="bg-sand animate-pulse rounded-card h-48" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />
      <main className="max-w-3xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="font-display text-abyss text-3xl font-bold">
            {district.name}
          </h1>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <span className="bg-deep text-white text-xs px-2 py-1 rounded-badge">
              {district.locale_type}
            </span>
            <span className="text-stone text-sm">{district.state}</span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            {
              label: "Enrollment",
              value: Number(district.enrollment).toLocaleString(),
            },
            { label: "FRL %", value: `${district.frl_pct}%` },
            { label: "ELL %", value: `${district.ell_pct}%` },
            { label: "Type", value: district.locale_type },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-chalk rounded-card shadow-card p-3 border border-pebble text-center"
            >
              <p className="text-xs text-stone">{stat.label}</p>
              <p className="text-lg font-bold text-abyss">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Members */}
        <div className="bg-chalk rounded-card shadow-card p-4 border border-pebble">
          <h2 className="font-display text-abyss text-lg font-bold mb-3">
            Members ({district.members.length})
          </h2>
          {district.members.length === 0 ? (
            <p className="text-stone text-sm">No members yet.</p>
          ) : (
            <div className="space-y-2">
              {district.members.map((member) => {
                const initials =
                  `${member.first_name?.[0] || ""}${member.last_name?.[0] || ""}`.toUpperCase();
                return (
                  <Link
                    key={member.id}
                    href={`/profile/${member.id}`}
                    className="flex items-center gap-3 p-2 rounded-input hover:bg-sand transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-foam text-current font-display font-bold text-xs flex items-center justify-center">
                      {initials}
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-obsidian">
                        {member.first_name} {member.last_name}
                      </span>
                      <span className="text-xs text-stone ml-2">
                        {member.role}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Data vintage footnote */}
        <p className="text-stone text-xs mt-4">
          Data source: NCES Common Core of Data, vintage {district.data_vintage}
        </p>
      </main>
    </div>
  );
}
