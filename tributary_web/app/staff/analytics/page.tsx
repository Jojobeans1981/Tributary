"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import NavHeader from "@/app/components/NavHeader";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Line, Bar, Doughnut } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

/* ---------- types ---------- */

interface MeData {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
}

interface AnalyticsData {
  summary: {
    total_members: number;
    messages_sent: number;
    match_acceptance_rate: number;
    avg_feedback_rating: number;
  };
  charts: {
    member_growth: { date: string; cumulative_count: number }[];
    problem_distribution: {
      id: number;
      title: string;
      selection_count: number;
    }[];
    message_volume: { date: string; count: number }[];
    top_district_pairs: {
      district_a_name: string;
      district_b_name: string;
      total_score: number;
    }[];
  };
}

/* ---------- component ---------- */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AnalyticsPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeData | null>(null);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [dateTo, setDateTo] = useState(
    () => new Date().toISOString().split("T")[0]
  );

  /* auth + role check */
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }
    apiFetch<MeData>("/api/users/me/").then((res) => {
      if (res.success && res.data) {
        setMe(res.data);
      }
    });
  }, [router]);

  /* fetch analytics */
  useEffect(() => {
    if (!me) return;
    setLoading(true);
    apiFetch<AnalyticsData>(
      `/api/staff/analytics/?date_from=${dateFrom}&date_to=${dateTo}`
    ).then((res) => {
      if (res.success && res.data) setData(res.data);
      setLoading(false);
    });
  }, [me, dateFrom, dateTo]);

  /* CSV export */
  const handleExport = () => {
    const token = localStorage.getItem("access_token");
    const url = `${API_BASE}/api/staff/analytics/export/?date_from=${dateFrom}&date_to=${dateTo}`;
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `tributary-analytics-${dateTo}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
      });
  };

  if (!me || loading) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-6xl mx-auto p-6 space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-sand animate-pulse rounded-card h-32" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) return null;

  /* chart data */
  const memberGrowthData = {
    labels: data.charts.member_growth.map((d) => d.date.slice(5)), // MM-DD
    datasets: [
      {
        label: "Members",
        data: data.charts.member_growth.map((d) => d.cumulative_count),
        borderColor: "#2563eb",
        backgroundColor: "rgba(37,99,235,0.1)",
        fill: true,
        tension: 0.3,
      },
    ],
  };

  const messageVolumeData = {
    labels: data.charts.message_volume.map((d) => d.date.slice(5)),
    datasets: [
      {
        label: "Messages",
        data: data.charts.message_volume.map((d) => d.count),
        backgroundColor: "#1e3a5f",
        borderRadius: 4,
      },
    ],
  };

  const problemDistData = {
    labels: data.charts.problem_distribution.map((d) => d.title),
    datasets: [
      {
        data: data.charts.problem_distribution.map((d) => d.selection_count),
        backgroundColor: [
          "#1e3a5f",
          "#2563eb",
          "#0ea5e9",
          "#06b6d4",
          "#14b8a6",
          "#10b981",
          "#84cc16",
          "#eab308",
          "#f97316",
          "#ef4444",
        ],
      },
    ],
  };

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />

      <main id="main-content" className="max-w-6xl mx-auto p-6" aria-label="Analytics dashboard">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <h1 className="font-display text-abyss text-2xl font-bold">
            Analytics Dashboard
          </h1>
          <div className="flex items-center gap-3">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              aria-label="Start date"
              className="border border-pebble rounded-input px-3 py-1.5 text-sm"
            />
            <span className="text-stone text-sm">to</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              aria-label="End date"
              className="border border-pebble rounded-input px-3 py-1.5 text-sm"
            />
            <button
              onClick={handleExport}
              className="bg-deep text-white text-sm font-bold px-4 py-2 rounded-input hover:bg-abyss transition-colors"
            >
              Export CSV
            </button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <SummaryCard
            label="Total Members"
            value={data.summary.total_members.toLocaleString()}
          />
          <SummaryCard
            label="Messages Sent"
            value={data.summary.messages_sent.toLocaleString()}
          />
          <SummaryCard
            label="Match Acceptance"
            value={`${data.summary.match_acceptance_rate}%`}
          />
          <SummaryCard
            label="Avg Feedback"
            value={`${data.summary.avg_feedback_rating}/5`}
          />
        </div>

        {/* Charts grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Member Growth */}
          <div className="bg-chalk rounded-card border border-pebble shadow-card p-4">
            <h2 className="font-display text-abyss font-bold mb-3">
              Member Growth
            </h2>
            <Line
              data={memberGrowthData}
              options={{
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                  x: { ticks: { maxTicksLimit: 10, font: { size: 10 } } },
                  y: { beginAtZero: true },
                },
              }}
            />
          </div>

          {/* Message Volume */}
          <div className="bg-chalk rounded-card border border-pebble shadow-card p-4">
            <h2 className="font-display text-abyss font-bold mb-3">
              Message Volume
            </h2>
            <Bar
              data={messageVolumeData}
              options={{
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                  x: { ticks: { maxTicksLimit: 10, font: { size: 10 } } },
                  y: { beginAtZero: true },
                },
              }}
            />
          </div>

          {/* Problem Distribution */}
          <div className="bg-chalk rounded-card border border-pebble shadow-card p-4">
            <h2 className="font-display text-abyss font-bold mb-3">
              Problem Distribution
            </h2>
            <div className="max-w-xs mx-auto">
              <Doughnut
                data={problemDistData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      position: "bottom",
                      labels: { font: { size: 10 }, boxWidth: 12 },
                    },
                  },
                }}
              />
            </div>
          </div>

          {/* Top District Pairs */}
          <div className="bg-chalk rounded-card border border-pebble shadow-card p-4">
            <h2 className="font-display text-abyss font-bold mb-3">
              Top District Pairs
            </h2>
            <div className="overflow-y-auto max-h-64">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-pebble text-left">
                    <th className="py-1.5 text-stone font-medium">
                      District A
                    </th>
                    <th className="py-1.5 text-stone font-medium">
                      District B
                    </th>
                    <th className="py-1.5 text-stone font-medium text-right">
                      Score
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.charts.top_district_pairs.map((pair, i) => (
                    <tr key={i} className="border-b border-pebble last:border-0">
                      <td className="py-1.5 text-obsidian">
                        {pair.district_a_name}
                      </td>
                      <td className="py-1.5 text-obsidian">
                        {pair.district_b_name}
                      </td>
                      <td className="py-1.5 text-current font-bold text-right">
                        {pair.total_score}
                      </td>
                    </tr>
                  ))}
                  {data.charts.top_district_pairs.length === 0 && (
                    <tr>
                      <td
                        colSpan={3}
                        className="py-4 text-center text-stone"
                      >
                        No data yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

/* ---------- summary card ---------- */

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-chalk rounded-card border border-pebble shadow-card p-4 text-center">
      <p className="text-stone text-xs mb-1">{label}</p>
      <p className="font-display text-abyss text-2xl font-bold">{value}</p>
    </div>
  );
}
