"use client";

import { useState, useEffect } from "react";
import { channelsApi } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import { Save, Plus, Trash2, Eye, EyeOff } from "lucide-react";

interface Integration {
  id: string;
  platform: string;
  display_name: string;
  phone_number_id: string;
  waba_id: string;
  is_active: boolean;
  ai_enabled: boolean;
  ai_system_prompt: string;
  ai_handoff_keywords: string[];
}

const DEFAULT_FORM = {
  platform: "whatsapp",
  display_name: "",
  phone_number_id: "",
  access_token: "",
  waba_id: "",
  ai_enabled: true,
  ai_system_prompt:
    "You are a helpful customer support assistant. Be concise, friendly, and professional.",
  ai_handoff_keywords: ["human", "agent"],
};

export default function SettingsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [showToken, setShowToken] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    channelsApi.list().then((res) => setIntegrations(res.data.results ?? res.data));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMsg("");
    try {
      const res = await channelsApi.create({
        ...form,
        ai_handoff_keywords: form.ai_handoff_keywords,
      });
      setIntegrations((prev) => [res.data, ...prev]);
      setForm(DEFAULT_FORM);
      setMsg("Integration saved successfully.");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setMsg(err?.response?.data?.detail || "Failed to save. Check your credentials.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    await channelsApi.delete(id);
    setIntegrations((prev) => prev.filter((i) => i.id !== id));
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />

      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl font-bold mb-1">Settings</h1>
          <p className="text-muted-foreground text-sm mb-8">
            Configure your channel integrations and AI agent behaviour.
          </p>

          {/* Existing integrations */}
          {integrations.length > 0 && (
            <div className="mb-8">
              <h2 className="font-semibold mb-3">Active Integrations</h2>
              <div className="flex flex-col gap-2">
                {integrations.map((int) => (
                  <div
                    key={int.id}
                    className="flex items-center justify-between p-3 rounded-xl border border-border bg-white"
                  >
                    <div>
                      <p className="font-medium text-sm">{int.display_name || int.platform}</p>
                      <p className="text-xs text-muted-foreground">
                        {int.phone_number_id} · AI {int.ai_enabled ? "on" : "off"}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDelete(int.id)}
                      className="text-destructive hover:bg-destructive/10 p-2 rounded-lg transition-colors"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Add new integration */}
          <div className="bg-white rounded-2xl border border-border p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-5">
              <Plus size={18} className="text-primary" />
              <h2 className="font-semibold">Add WhatsApp Integration</h2>
            </div>

            <div className="flex flex-col gap-4">
              <Field label="Display Name">
                <input
                  className="input"
                  placeholder="e.g. My Business WhatsApp"
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                />
              </Field>

              <Field label="Phone Number ID">
                <input
                  className="input"
                  placeholder="From Meta Business Suite"
                  value={form.phone_number_id}
                  onChange={(e) => setForm({ ...form, phone_number_id: e.target.value })}
                />
              </Field>

              <Field label="WhatsApp Business Account ID">
                <input
                  className="input"
                  placeholder="WABA ID"
                  value={form.waba_id}
                  onChange={(e) => setForm({ ...form, waba_id: e.target.value })}
                />
              </Field>

              <Field label="Permanent Access Token">
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showToken ? "text" : "password"}
                    placeholder="EAAxxxx..."
                    value={form.access_token}
                    onChange={(e) => setForm({ ...form, access_token: e.target.value })}
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  >
                    {showToken ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </Field>

              <Field label="AI System Prompt">
                <textarea
                  className="input min-h-[90px] resize-none"
                  value={form.ai_system_prompt}
                  onChange={(e) => setForm({ ...form, ai_system_prompt: e.target.value })}
                />
              </Field>

              <Field label="Human Handoff Keywords (comma separated)">
                <input
                  className="input"
                  placeholder="human, agent, speak to someone"
                  value={form.ai_handoff_keywords.join(", ")}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      ai_handoff_keywords: e.target.value.split(",").map((s) => s.trim()),
                    })
                  }
                />
              </Field>

              {msg && (
                <p
                  className={`text-xs px-3 py-2 rounded-lg ${
                    msg.includes("success")
                      ? "bg-primary/10 text-primary"
                      : "bg-destructive/10 text-destructive"
                  }`}
                >
                  {msg}
                </p>
              )}

              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 justify-center bg-primary text-white rounded-xl py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60"
              >
                <Save size={15} />
                {saving ? "Saving..." : "Save Integration"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .input {
          width: 100%;
          border: 1px solid hsl(var(--border));
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
          outline: none;
          background: transparent;
        }
        .input:focus {
          ring: 2px solid hsl(var(--primary) / 50%);
          border-color: hsl(var(--primary));
        }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
    </div>
  );
}
