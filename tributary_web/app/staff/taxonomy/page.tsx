"use client";

import { useState, useEffect, useCallback } from "react";
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

interface Statement {
  id: number;
  title: string;
  description: string;
  category: string;
  is_active: boolean;
  version: number;
  member_count: number;
}

/* ---------- component ---------- */

export default function TaxonomyPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeData | null>(null);
  const [statements, setStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState("");

  /* modal state */
  const [showAdd, setShowAdd] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showRetire, setShowRetire] = useState(false);
  const [editTarget, setEditTarget] = useState<Statement | null>(null);
  const [retireTarget, setRetireTarget] = useState<Statement | null>(null);

  /* form fields */
  const [formTitle, setFormTitle] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formCategory, setFormCategory] = useState("");

  /* auth + role check */
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    apiFetch<MeData>("/api/users/me/").then((res) => {
      if (res.success && res.data) {
        if (!["UPSTREAM_STAFF", "PLATFORM_ADMIN"].includes(res.data.role)) {
          router.replace("/dashboard");
          return;
        }
        setMe(res.data);
      }
    });
  }, [router]);

  /* fetch taxonomy */
  const fetchStatements = useCallback(() => {
    apiFetch<Statement[]>("/api/staff/taxonomy/").then((res) => {
      if (res.success && res.data) setStatements(res.data);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (me) fetchStatements();
  }, [me, fetchStatements]);

  /* auto-dismiss toast */
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  /* ---------- handlers ---------- */

  const handleAdd = async () => {
    const res = await apiFetch<Statement>("/api/staff/taxonomy/", {
      method: "POST",
      body: JSON.stringify({
        title: formTitle.trim(),
        description: formDesc.trim(),
        category: formCategory.trim(),
      }),
    });
    if (res.success) {
      setToast("Statement created.");
      setShowAdd(false);
      resetForm();
      fetchStatements();
    } else {
      setToast(res.error?.message || "Failed to create statement.");
    }
  };

  const openEdit = (s: Statement) => {
    setEditTarget(s);
    setFormTitle(s.title);
    setFormDesc(s.description);
    setFormCategory(s.category);
    setShowEdit(true);
  };

  const handleEdit = async () => {
    if (!editTarget) return;
    const res = await apiFetch<Statement>(
      `/api/staff/taxonomy/${editTarget.id}/`,
      {
        method: "PATCH",
        body: JSON.stringify({
          title: formTitle.trim(),
          description: formDesc.trim(),
          category: formCategory.trim(),
        }),
      }
    );
    if (res.success && res.data) {
      setToast(`Updated to version ${res.data.version}.`);
      setShowEdit(false);
      setEditTarget(null);
      resetForm();
      fetchStatements();
    } else {
      setToast(res.error?.message || "Failed to update statement.");
    }
  };

  const openRetire = (s: Statement) => {
    setRetireTarget(s);
    setShowRetire(true);
  };

  const handleRetire = async () => {
    if (!retireTarget) return;
    const res = await apiFetch<{ member_count: number; message: string }>(
      `/api/staff/taxonomy/${retireTarget.id}/retire/`,
      { method: "POST" }
    );
    if (res.success) {
      setToast(res.data?.message || "Statement retired.");
      setShowRetire(false);
      setRetireTarget(null);
      fetchStatements();
    } else {
      setToast(res.error?.message || "Failed to retire statement.");
    }
  };

  const resetForm = () => {
    setFormTitle("");
    setFormDesc("");
    setFormCategory("");
  };

  /* ---------- render ---------- */

  if (loading) {
    return (
      <div className="bg-mist min-h-screen">
        <div className="bg-abyss h-16" />
        <div className="max-w-5xl mx-auto p-6 space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-sand animate-pulse rounded-card h-14" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-mist min-h-screen">
      <NavHeader user={me} />

      <main id="main-content" className="max-w-5xl mx-auto p-6" aria-label="Taxonomy management">
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-display text-abyss text-2xl font-bold">
            Taxonomy Management
          </h1>
          <button
            onClick={() => {
              resetForm();
              setShowAdd(true);
            }}
            className="bg-current text-white text-sm font-bold px-4 py-2 rounded-input hover:bg-deep transition-colors"
          >
            Add Statement
          </button>
        </div>

        {/* Toast */}
        {toast && (
          <div className="bg-go-light border border-go text-go rounded-card p-3 mb-4 flex justify-between items-center">
            <span className="text-sm">{toast}</span>
            <button
              onClick={() => setToast("")}
              className="text-go font-bold"
            >
              &times;
            </button>
          </div>
        )}

        {/* Table */}
        <div className="bg-chalk rounded-card border border-pebble overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-sand border-b border-pebble text-left">
                  <th className="px-4 py-3 font-display text-abyss font-bold">
                    ID
                  </th>
                  <th className="px-4 py-3 font-display text-abyss font-bold">
                    Title
                  </th>
                  <th className="px-4 py-3 font-display text-abyss font-bold">
                    Category
                  </th>
                  <th className="px-4 py-3 font-display text-abyss font-bold">
                    Status
                  </th>
                  <th className="px-4 py-3 font-display text-abyss font-bold">
                    Version
                  </th>
                  <th className="px-4 py-3 font-display text-abyss font-bold">
                    Members
                  </th>
                  <th className="px-4 py-3 font-display text-abyss font-bold">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {statements.map((s) => (
                  <tr
                    key={s.id}
                    className={`border-b border-pebble last:border-b-0 ${
                      !s.is_active ? "text-stone italic opacity-70" : ""
                    }`}
                  >
                    <td className="px-4 py-3 text-obsidian">{s.id}</td>
                    <td className="px-4 py-3 text-obsidian font-medium">
                      {s.title}
                    </td>
                    <td className="px-4 py-3 text-obsidian">{s.category}</td>
                    <td className="px-4 py-3">
                      {s.is_active ? (
                        <span className="bg-go-light text-go text-xs font-bold px-2 py-0.5 rounded-badge">
                          Active
                        </span>
                      ) : (
                        <span className="bg-stop-light text-stop text-xs font-bold px-2 py-0.5 rounded-badge">
                          Retired
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-obsidian">v{s.version}</td>
                    <td className="px-4 py-3 text-obsidian">
                      {s.member_count}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => openEdit(s)}
                          className="text-current text-xs font-bold hover:underline"
                        >
                          Edit
                        </button>
                        {s.is_active && (
                          <button
                            onClick={() => openRetire(s)}
                            className="text-stop text-xs font-bold hover:underline"
                          >
                            Retire
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {statements.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-4 py-8 text-center text-stone"
                    >
                      No problem statements found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Add Modal */}
      {showAdd && (
        <Modal title="Add Statement" onClose={() => setShowAdd(false)}>
          <StatementForm
            title={formTitle}
            description={formDesc}
            category={formCategory}
            onTitleChange={setFormTitle}
            onDescChange={setFormDesc}
            onCatChange={setFormCategory}
          />
          <button
            onClick={handleAdd}
            disabled={
              !formTitle.trim() || !formDesc.trim() || !formCategory.trim()
            }
            className="bg-current text-white text-sm font-bold px-4 py-2 rounded-input hover:bg-deep disabled:bg-pebble transition-colors mt-4"
          >
            Create
          </button>
        </Modal>
      )}

      {/* Edit Modal */}
      {showEdit && editTarget && (
        <Modal title="Edit Statement" onClose={() => setShowEdit(false)}>
          <StatementForm
            title={formTitle}
            description={formDesc}
            category={formCategory}
            onTitleChange={setFormTitle}
            onDescChange={setFormDesc}
            onCatChange={setFormCategory}
          />
          <button
            onClick={handleEdit}
            disabled={
              !formTitle.trim() || !formDesc.trim() || !formCategory.trim()
            }
            className="bg-current text-white text-sm font-bold px-4 py-2 rounded-input hover:bg-deep disabled:bg-pebble transition-colors mt-4"
          >
            Save Changes
          </button>
        </Modal>
      )}

      {/* Retire Confirm */}
      {showRetire && retireTarget && (
        <Modal title="Retire Statement" onClose={() => setShowRetire(false)}>
          <p className="text-sm text-obsidian mb-4">
            Are you sure you want to retire{" "}
            <strong>&ldquo;{retireTarget.title}&rdquo;</strong>? Members who
            have selected this statement will retain their selection, but it
            will no longer appear for new selections.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleRetire}
              className="bg-stop text-white text-sm font-bold px-4 py-2 rounded-input hover:opacity-90 transition-colors"
            >
              Retire
            </button>
            <button
              onClick={() => setShowRetire(false)}
              className="bg-pebble text-obsidian text-sm font-bold px-4 py-2 rounded-input hover:bg-stone hover:text-white transition-colors"
            >
              Cancel
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

/* ---------- reusable components ---------- */

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
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="text-stone text-xl font-bold"
          >
            &times;
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function StatementForm({
  title,
  description,
  category,
  onTitleChange,
  onDescChange,
  onCatChange,
}: {
  title: string;
  description: string;
  category: string;
  onTitleChange: (v: string) => void;
  onDescChange: (v: string) => void;
  onCatChange: (v: string) => void;
}) {
  return (
    <>
      <label className="block text-sm text-obsidian mb-1">Title</label>
      <input
        value={title}
        onChange={(e) => onTitleChange(e.target.value)}
        className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
        placeholder="Problem statement title"
      />
      <label className="block text-sm text-obsidian mb-1">Description</label>
      <textarea
        value={description}
        onChange={(e) => onDescChange(e.target.value)}
        rows={3}
        className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
        placeholder="Detailed description"
      />
      <label className="block text-sm text-obsidian mb-1">Category</label>
      <input
        value={category}
        onChange={(e) => onCatChange(e.target.value)}
        className="w-full border border-pebble rounded-input px-3 py-2 text-sm mb-3"
        placeholder="e.g. Phonics, Comprehension"
      />
    </>
  );
}
