"use client";

import { useState, useEffect, useCallback } from "react";
import { channelsApi, aiApi } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import {
  MessageSquare,
  Send,
  Copy,
  Check,
  Trash2,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  Zap,
  Globe,
  Bot,
  Settings,
  Plus,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Platform = "whatsapp" | "messenger" | "instagram" | "telegram" | "discord" | "web_chat";

interface Integration {
  id: string;
  platform: Platform;
  display_name: string;
  phone_number_id: string;
  waba_id: string;
  page_id: string;
  instagram_business_account_id: string;
  telegram_bot_username: string;
  discord_guild_id: string;
  web_chat_widget_key: string;
  is_active: boolean;
  ai_enabled: boolean;
  ai_system_prompt: string;
  ai_handoff_keywords: string[];
  created_at: string;
}

interface WebhookInfo {
  webhook_url: string;
  verify_token: string;
}

// ─── Channel Config ───────────────────────────────────────────────────────────

const CHANNELS: {
  id: Platform;
  label: string;
  icon: string;
  color: string;
  bgColor: string;
  description: string;
}[] = [
  {
    id: "whatsapp",
    label: "WhatsApp",
    icon: "💬",
    color: "text-green-700",
    bgColor: "bg-green-50 border-green-200",
    description: "Connect via WhatsApp Cloud API",
  },
  {
    id: "messenger",
    label: "Facebook Messenger",
    icon: "📘",
    color: "text-blue-700",
    bgColor: "bg-blue-50 border-blue-200",
    description: "Connect a Facebook Page",
  },
  {
    id: "instagram",
    label: "Instagram",
    icon: "📸",
    color: "text-pink-700",
    bgColor: "bg-pink-50 border-pink-200",
    description: "Connect Instagram DMs via Meta API",
  },
  {
    id: "telegram",
    label: "Telegram",
    icon: "✈️",
    color: "text-sky-700",
    bgColor: "bg-sky-50 border-sky-200",
    description: "Connect a Telegram Bot",
  },
  {
    id: "discord",
    label: "Discord",
    icon: "🎮",
    color: "text-indigo-700",
    bgColor: "bg-indigo-50 border-indigo-200",
    description: "Connect a Discord Server Bot",
  },
  {
    id: "web_chat",
    label: "Web Chat",
    icon: "🌐",
    color: "text-violet-700",
    bgColor: "bg-violet-50 border-violet-200",
    description: "Embed a chat widget on your website",
  },
];

const PLATFORM_LABELS: Record<Platform, string> = {
  whatsapp: "WhatsApp",
  messenger: "Facebook Messenger",
  instagram: "Instagram",
  telegram: "Telegram",
  discord: "Discord",
  web_chat: "Web Chat",
};

const PLATFORM_ICONS: Record<Platform, string> = {
  whatsapp: "💬",
  messenger: "📘",
  instagram: "📸",
  telegram: "✈️",
  discord: "🎮",
  web_chat: "🌐",
};

// ─── Default Form State ───────────────────────────────────────────────────────

const makeDefaultForm = (platform: Platform) => ({
  platform,
  display_name: "",
  // WhatsApp
  phone_number_id: "",
  access_token: "",
  waba_id: "",
  app_secret: "",
  // Messenger / Instagram
  page_id: "",
  page_access_token: "",
  instagram_business_account_id: "",
  // Telegram
  telegram_bot_token: "",
  telegram_bot_username: "",
  // Discord
  discord_bot_token: "",
  discord_guild_id: "",
  discord_channel_id: "",
  // Web Chat
  web_chat_allowed_origins: "",
  // AI
  ai_enabled: true,
  ai_system_prompt:
    "You are a helpful customer support assistant. Be concise, friendly, and professional. If you cannot help, say so and offer to connect them with a human agent.",
  ai_handoff_keywords: ["human", "agent", "speak to someone"],
});

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"channels" | "ai" | "webhook">("channels");
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>("whatsapp");
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [webhookInfo, setWebhookInfo] = useState<WebhookInfo | null>(null);
  const [form, setForm] = useState(makeDefaultForm("whatsapp"));
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Test message state
  const [testIntegrationId, setTestIntegrationId] = useState("");
  const [testTo, setTestTo] = useState("");
  const [testMessage, setTestMessage] = useState(
    "👋 Hello! This is a test message from Wow Chat."
  );
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; text: string } | null>(null);

  const [copied, setCopied] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    const [intRes, whRes] = await Promise.all([
      channelsApi.list().catch(() => ({ data: [] })),
      aiApi.webhookInfo().catch(() => ({ data: null })),
    ]);
    setIntegrations(intRes.data.results ?? intRes.data);
    if (whRes.data) setWebhookInfo(whRes.data);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handlePlatformSelect = (p: Platform) => {
    setSelectedPlatform(p);
    setForm(makeDefaultForm(p));
    setMsg(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await channelsApi.create({
        ...form,
        ai_handoff_keywords: form.ai_handoff_keywords,
      });
      await loadData();
      setForm(makeDefaultForm(selectedPlatform));
      setMsg({ text: "Integration saved successfully.", ok: true });
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string; non_field_errors?: string[] } } };
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.non_field_errors?.[0] ||
        "Failed to save. Check your credentials.";
      setMsg({ text: detail, ok: false });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remove this integration?")) return;
    await channelsApi.delete(id);
    setIntegrations((prev) => prev.filter((i) => i.id !== id));
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const toggleSecret = (key: string) =>
    setShowSecrets((prev) => ({ ...prev, [key]: !prev[key] }));

  const handleSendTest = async () => {
    if (!testIntegrationId || !testTo) {
      setTestResult({ ok: false, text: "Select an integration and enter a phone number." });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await aiApi.sendTest({
        integration_id: testIntegrationId,
        to: testTo,
        message: testMessage,
      });
      setTestResult({
        ok: true,
        text: `Message sent! ID: ${res.data.message_id || "—"}`,
      });
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string } } };
      setTestResult({
        ok: false,
        text: err?.response?.data?.error || "Failed to send message.",
      });
    } finally {
      setTesting(false);
    }
  };

  const whatsappIntegrations = integrations.filter((i) => i.platform === "whatsapp");

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />

      <div className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="border-b border-border px-8 py-5 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <Settings size={18} className="text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight">Settings</h1>
              <p className="text-xs text-muted-foreground">
                Manage channels, AI agent and webhook configuration
              </p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4">
            {(["channels", "ai", "webhook"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
                  activeTab === tab
                    ? "bg-primary text-white"
                    : "text-muted-foreground hover:bg-muted"
                }`}
              >
                {tab === "channels" ? "📡 Channels" : tab === "ai" ? "🤖 AI Agent" : "🔗 Webhook"}
              </button>
            ))}
          </div>
        </div>

        <div className="p-8 max-w-4xl mx-auto">
          {/* ── CHANNELS TAB ── */}
          {activeTab === "channels" && (
            <div className="space-y-8">
              {/* Architecture Overview */}
              <div className="bg-gradient-to-br from-primary/5 to-primary/10 rounded-2xl border border-primary/20 p-6">
                <h2 className="font-semibold text-sm mb-4 flex items-center gap-2">
                  <Globe size={15} className="text-primary" />
                  Connected Channels → API Gateway → Message Broker → AI Agent + Unified Inbox
                </h2>
                <div className="flex flex-wrap gap-2">
                  {CHANNELS.map((ch) => {
                    const count = integrations.filter((i) => i.platform === ch.id).length;
                    return (
                      <div
                        key={ch.id}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium ${ch.bgColor} ${ch.color}`}
                      >
                        <span>{ch.icon}</span>
                        <span>{ch.label}</span>
                        {count > 0 && (
                          <span className="ml-1 bg-white/60 rounded-full px-1.5 py-0.5 text-[10px]">
                            {count}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Active Integrations */}
              {integrations.length > 0 && (
                <div>
                  <h2 className="font-semibold text-sm mb-3 flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-green-600" />
                    Active Integrations ({integrations.length})
                  </h2>
                  <div className="flex flex-col gap-2">
                    {integrations.map((intg) => (
                      <div
                        key={intg.id}
                        className="bg-white rounded-xl border border-border overflow-hidden"
                      >
                        <div className="flex items-center justify-between p-4">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl">{PLATFORM_ICONS[intg.platform]}</span>
                            <div>
                              <p className="font-medium text-sm">
                                {intg.display_name || PLATFORM_LABELS[intg.platform]}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {PLATFORM_LABELS[intg.platform]}
                                {intg.phone_number_id ? ` · ${intg.phone_number_id}` : ""}
                                {intg.telegram_bot_username
                                  ? ` · @${intg.telegram_bot_username}`
                                  : ""}
                                {intg.discord_guild_id
                                  ? ` · Guild ${intg.discord_guild_id}`
                                  : ""}
                                {" · "} AI {intg.ai_enabled ? "✅" : "⏸️"}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {intg.platform === "web_chat" && intg.web_chat_widget_key && (
                              <button
                                onClick={() => handleCopy(intg.web_chat_widget_key, intg.id)}
                                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-muted"
                              >
                                {copied === intg.id ? (
                                  <Check size={12} className="text-green-600" />
                                ) : (
                                  <Copy size={12} />
                                )}
                                Widget Key
                              </button>
                            )}
                            <button
                              onClick={() =>
                                setExpandedId(expandedId === intg.id ? null : intg.id)
                              }
                              className="text-muted-foreground hover:text-foreground p-1.5 rounded-lg hover:bg-muted"
                            >
                              {expandedId === intg.id ? (
                                <ChevronUp size={15} />
                              ) : (
                                <ChevronDown size={15} />
                              )}
                            </button>
                            <button
                              onClick={() => handleDelete(intg.id)}
                              className="text-destructive/70 hover:text-destructive hover:bg-destructive/10 p-1.5 rounded-lg transition-colors"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </div>
                        {expandedId === intg.id && (
                          <div className="border-t border-border px-4 py-3 bg-muted/30 text-xs text-muted-foreground space-y-1">
                            {intg.phone_number_id && (
                              <p>Phone Number ID: {intg.phone_number_id}</p>
                            )}
                            {intg.waba_id && <p>WABA ID: {intg.waba_id}</p>}
                            {intg.page_id && <p>Page ID: {intg.page_id}</p>}
                            {intg.instagram_business_account_id && (
                              <p>IG Account ID: {intg.instagram_business_account_id}</p>
                            )}
                            {intg.telegram_bot_username && (
                              <p>Bot: @{intg.telegram_bot_username}</p>
                            )}
                            {intg.discord_guild_id && (
                              <p>Guild: {intg.discord_guild_id}</p>
                            )}
                            {intg.web_chat_widget_key && (
                              <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                  <span>Widget Key:</span>
                                  <code className="bg-muted px-1.5 py-0.5 rounded text-[10px] font-mono">
                                    {intg.web_chat_widget_key}
                                  </code>
                                  <button
                                    onClick={() =>
                                      handleCopy(intg.web_chat_widget_key, `wk-${intg.id}`)
                                    }
                                    className="hover:text-foreground"
                                  >
                                    {copied === `wk-${intg.id}` ? (
                                      <Check size={11} className="text-green-600" />
                                    ) : (
                                      <Copy size={11} />
                                    )}
                                  </button>
                                </div>
                                <div className="mt-2">
                                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1">
                                    Embed Code
                                  </p>
                                  <div className="relative group">
                                    <pre className="bg-[#1e1e2e] text-[#cdd6f4] text-[10px] rounded-lg px-3 py-2.5 overflow-x-auto leading-relaxed whitespace-pre-wrap break-all font-mono">
{`<script
  src="https://wow.gpayauto.org/webchat/widget.js"
  data-widget-key="${intg.web_chat_widget_key}"
  data-bot-name="${intg.display_name || "AI Assistant"}"
></script>`}
                                    </pre>
                                    <button
                                      onClick={() =>
                                        handleCopy(
                                          `<script\n  src="https://wow.gpayauto.org/webchat/widget.js"\n  data-widget-key="${intg.web_chat_widget_key}"\n  data-bot-name="${intg.display_name || "AI Assistant"}"\n></script>`,
                                          `embed-${intg.id}`
                                        )
                                      }
                                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white/10 hover:bg-white/20 text-white rounded p-1"
                                    >
                                      {copied === `embed-${intg.id}` ? (
                                        <Check size={11} className="text-green-400" />
                                      ) : (
                                        <Copy size={11} />
                                      )}
                                    </button>
                                  </div>
                                  <p className="text-[10px] text-muted-foreground mt-1">
                                    Paste this before <code className="font-mono">&lt;/body&gt;</code> on any page.
                                  </p>
                                </div>
                              </div>
                            )}
                            <p>
                              AI System Prompt:{" "}
                              {intg.ai_system_prompt.slice(0, 80)}
                              {intg.ai_system_prompt.length > 80 ? "…" : ""}
                            </p>
                            <p>
                              Handoff Keywords: {intg.ai_handoff_keywords.join(", ")}
                            </p>
                            <p>Added: {new Date(intg.created_at).toLocaleDateString()}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Add Integration */}
              <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
                <div className="p-5 border-b border-border">
                  <div className="flex items-center gap-2 mb-4">
                    <Plus size={16} className="text-primary" />
                    <h2 className="font-semibold text-sm">Add New Integration</h2>
                  </div>

                  {/* Channel selector */}
                  <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                    {CHANNELS.map((ch) => (
                      <button
                        key={ch.id}
                        onClick={() => handlePlatformSelect(ch.id)}
                        className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 transition-all text-center ${
                          selectedPlatform === ch.id
                            ? `${ch.bgColor} border-current ${ch.color}`
                            : "border-border hover:border-muted-foreground/30 hover:bg-muted/30"
                        }`}
                      >
                        <span className="text-2xl leading-none">{ch.icon}</span>
                        <span className="text-[11px] font-medium leading-tight">{ch.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-5">
                  <div className="flex flex-col gap-4">
                    <Field label="Display Name">
                      <input
                        className="inp"
                        placeholder={`e.g. My ${PLATFORM_LABELS[selectedPlatform]}`}
                        value={form.display_name}
                        onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                      />
                    </Field>

                    {/* WhatsApp fields */}
                    {selectedPlatform === "whatsapp" && (
                      <>
                        <Field label="Phone Number ID">
                          <input
                            className="inp"
                            placeholder="From Meta Business Suite → WhatsApp"
                            value={form.phone_number_id}
                            onChange={(e) =>
                              setForm({ ...form, phone_number_id: e.target.value })
                            }
                          />
                        </Field>
                        <Field label="WhatsApp Business Account ID (WABA ID)">
                          <input
                            className="inp"
                            placeholder="WABA ID from Meta Business Manager"
                            value={form.waba_id}
                            onChange={(e) => setForm({ ...form, waba_id: e.target.value })}
                          />
                        </Field>
                        <Field label="Permanent Access Token">
                          <SecretInput
                            value={form.access_token}
                            placeholder="EAAxxxx..."
                            fieldKey="wa_token"
                            show={!!showSecrets["wa_token"]}
                            onToggle={() => toggleSecret("wa_token")}
                            onChange={(v) => setForm({ ...form, access_token: v })}
                          />
                        </Field>
                        <Field label="App Secret (for webhook signature verification)">
                          <SecretInput
                            value={form.app_secret}
                            placeholder="Meta App Secret"
                            fieldKey="wa_secret"
                            show={!!showSecrets["wa_secret"]}
                            onToggle={() => toggleSecret("wa_secret")}
                            onChange={(v) => setForm({ ...form, app_secret: v })}
                          />
                        </Field>
                      </>
                    )}

                    {/* Messenger fields */}
                    {selectedPlatform === "messenger" && (
                      <>
                        <Field label="Facebook Page ID">
                          <input
                            className="inp"
                            placeholder="Your Facebook Page ID"
                            value={form.page_id}
                            onChange={(e) => setForm({ ...form, page_id: e.target.value })}
                          />
                        </Field>
                        <Field label="Page Access Token">
                          <SecretInput
                            value={form.page_access_token}
                            placeholder="EAAxxxx..."
                            fieldKey="fb_token"
                            show={!!showSecrets["fb_token"]}
                            onToggle={() => toggleSecret("fb_token")}
                            onChange={(v) => setForm({ ...form, page_access_token: v })}
                          />
                        </Field>
                        <Field label="App Secret">
                          <SecretInput
                            value={form.app_secret}
                            placeholder="Meta App Secret"
                            fieldKey="fb_secret"
                            show={!!showSecrets["fb_secret"]}
                            onToggle={() => toggleSecret("fb_secret")}
                            onChange={(v) => setForm({ ...form, app_secret: v })}
                          />
                        </Field>
                      </>
                    )}

                    {/* Instagram fields */}
                    {selectedPlatform === "instagram" && (
                      <>
                        <Field label="Facebook Page ID (connected to Instagram)">
                          <input
                            className="inp"
                            placeholder="Your Facebook Page ID"
                            value={form.page_id}
                            onChange={(e) => setForm({ ...form, page_id: e.target.value })}
                          />
                        </Field>
                        <Field label="Instagram Business Account ID">
                          <input
                            className="inp"
                            placeholder="Instagram Business Account ID"
                            value={form.instagram_business_account_id}
                            onChange={(e) =>
                              setForm({
                                ...form,
                                instagram_business_account_id: e.target.value,
                              })
                            }
                          />
                        </Field>
                        <Field label="Page Access Token">
                          <SecretInput
                            value={form.page_access_token}
                            placeholder="EAAxxxx..."
                            fieldKey="ig_token"
                            show={!!showSecrets["ig_token"]}
                            onToggle={() => toggleSecret("ig_token")}
                            onChange={(v) => setForm({ ...form, page_access_token: v })}
                          />
                        </Field>
                        <Field label="App Secret">
                          <SecretInput
                            value={form.app_secret}
                            placeholder="Meta App Secret"
                            fieldKey="ig_secret"
                            show={!!showSecrets["ig_secret"]}
                            onToggle={() => toggleSecret("ig_secret")}
                            onChange={(v) => setForm({ ...form, app_secret: v })}
                          />
                        </Field>
                      </>
                    )}

                    {/* Telegram fields */}
                    {selectedPlatform === "telegram" && (
                      <>
                        <Field label="Bot Token">
                          <SecretInput
                            value={form.telegram_bot_token}
                            placeholder="1234567890:ABCdefGHIjklMNOpqrSTUvwxyz"
                            fieldKey="tg_token"
                            show={!!showSecrets["tg_token"]}
                            onToggle={() => toggleSecret("tg_token")}
                            onChange={(v) => setForm({ ...form, telegram_bot_token: v })}
                          />
                        </Field>
                        <Field label="Bot Username">
                          <input
                            className="inp"
                            placeholder="@MyBot (without @)"
                            value={form.telegram_bot_username}
                            onChange={(e) =>
                              setForm({ ...form, telegram_bot_username: e.target.value })
                            }
                          />
                        </Field>
                        <div className="text-xs text-muted-foreground bg-muted/50 rounded-xl p-3">
                          📌 Create your bot via <strong>@BotFather</strong> on Telegram, then set
                          the webhook URL to:{" "}
                          <code className="font-mono bg-muted px-1 rounded">
                            {webhookInfo?.webhook_url?.replace("whatsapp", "telegram") ||
                              "https://wow.gpayauto.org/webhooks/telegram/"}
                          </code>
                        </div>
                      </>
                    )}

                    {/* Discord fields */}
                    {selectedPlatform === "discord" && (
                      <>
                        <Field label="Bot Token">
                          <SecretInput
                            value={form.discord_bot_token}
                            placeholder="Discord Bot Token from Developer Portal"
                            fieldKey="dc_token"
                            show={!!showSecrets["dc_token"]}
                            onToggle={() => toggleSecret("dc_token")}
                            onChange={(v) => setForm({ ...form, discord_bot_token: v })}
                          />
                        </Field>
                        <Field label="Guild (Server) ID">
                          <input
                            className="inp"
                            placeholder="Right-click server → Copy ID"
                            value={form.discord_guild_id}
                            onChange={(e) =>
                              setForm({ ...form, discord_guild_id: e.target.value })
                            }
                          />
                        </Field>
                        <Field label="Channel ID (for incoming messages)">
                          <input
                            className="inp"
                            placeholder="Right-click channel → Copy ID"
                            value={form.discord_channel_id}
                            onChange={(e) =>
                              setForm({ ...form, discord_channel_id: e.target.value })
                            }
                          />
                        </Field>
                      </>
                    )}

                    {/* Web Chat fields */}
                    {selectedPlatform === "web_chat" && (
                      <>
                        <Field label="Allowed Origins (one per line)">
                          <textarea
                            className="inp min-h-[80px] resize-none font-mono text-xs"
                            placeholder={"https://yourdomain.com\nhttps://app.yourdomain.com"}
                            value={form.web_chat_allowed_origins}
                            onChange={(e) =>
                              setForm({ ...form, web_chat_allowed_origins: e.target.value })
                            }
                          />
                        </Field>
                        <div className="text-xs text-muted-foreground bg-muted/50 rounded-xl p-3">
                          🔑 A unique <strong>Widget Key</strong> will be generated automatically.
                          Embed the widget on your site using that key.
                        </div>
                      </>
                    )}

                    {/* AI section — all platforms */}
                    <div className="border-t border-border pt-4 mt-2 space-y-4">
                      <div className="flex items-center gap-2">
                        <Bot size={15} className="text-primary" />
                        <span className="text-sm font-semibold">AI Agent Configuration</span>
                      </div>
                      <label className="flex items-center gap-3 cursor-pointer select-none">
                        <div
                          onClick={() => setForm({ ...form, ai_enabled: !form.ai_enabled })}
                          className={`w-10 h-5 rounded-full transition-colors relative ${
                            form.ai_enabled ? "bg-primary" : "bg-muted-foreground/30"
                          }`}
                        >
                          <span
                            className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                              form.ai_enabled ? "translate-x-5" : ""
                            }`}
                          />
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {form.ai_enabled
                            ? "AI auto-reply enabled"
                            : "AI disabled — manual replies only"}
                        </span>
                      </label>

                      <Field label="System Prompt">
                        <textarea
                          className="inp min-h-[90px] resize-none"
                          value={form.ai_system_prompt}
                          onChange={(e) =>
                            setForm({ ...form, ai_system_prompt: e.target.value })
                          }
                        />
                      </Field>

                      <Field label="Human Handoff Keywords (comma separated)">
                        <input
                          className="inp"
                          placeholder="human, agent, speak to someone, help"
                          value={form.ai_handoff_keywords.join(", ")}
                          onChange={(e) =>
                            setForm({
                              ...form,
                              ai_handoff_keywords: e.target.value
                                .split(",")
                                .map((s) => s.trim())
                                .filter(Boolean),
                            })
                          }
                        />
                      </Field>
                    </div>

                    {msg && (
                      <div
                        className={`flex items-center gap-2 text-xs px-3 py-2.5 rounded-xl ${
                          msg.ok
                            ? "bg-green-50 text-green-700 border border-green-200"
                            : "bg-destructive/10 text-destructive border border-destructive/20"
                        }`}
                      >
                        {msg.ok ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                        {msg.text}
                      </div>
                    )}

                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="flex items-center gap-2 justify-center bg-primary text-white rounded-xl py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60"
                    >
                      {saving ? (
                        <Loader2 size={15} className="animate-spin" />
                      ) : (
                        <Plus size={15} />
                      )}
                      {saving ? "Saving…" : `Add ${PLATFORM_LABELS[selectedPlatform]} Integration`}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── AI TAB ── */}
          {activeTab === "ai" && (
            <div className="space-y-6">
              <div className="bg-white rounded-2xl border border-border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-5">
                  <Zap size={16} className="text-amber-500" />
                  <h2 className="font-semibold text-sm">Send Test Message</h2>
                </div>
                <p className="text-xs text-muted-foreground mb-5">
                  Verify your WhatsApp integration is working by sending a live test message.
                </p>

                <div className="flex flex-col gap-4">
                  <Field label="Select WhatsApp Integration">
                    <select
                      className="inp"
                      value={testIntegrationId}
                      onChange={(e) => setTestIntegrationId(e.target.value)}
                    >
                      <option value="">— choose integration —</option>
                      {whatsappIntegrations.map((i) => (
                        <option key={i.id} value={i.id}>
                          {i.display_name || i.phone_number_id}
                        </option>
                      ))}
                    </select>
                  </Field>
                  {whatsappIntegrations.length === 0 && (
                    <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
                      ⚠️ No active WhatsApp integrations. Add one in the Channels tab first.
                    </p>
                  )}

                  <Field label="Recipient Phone Number">
                    <input
                      className="inp"
                      placeholder="+8801XXXXXXXXX (include country code)"
                      value={testTo}
                      onChange={(e) => setTestTo(e.target.value)}
                    />
                  </Field>

                  <Field label="Message">
                    <textarea
                      className="inp min-h-[80px] resize-none"
                      value={testMessage}
                      onChange={(e) => setTestMessage(e.target.value)}
                    />
                  </Field>

                  {testResult && (
                    <div
                      className={`flex items-start gap-2 text-xs px-3 py-2.5 rounded-xl ${
                        testResult.ok
                          ? "bg-green-50 text-green-700 border border-green-200"
                          : "bg-destructive/10 text-destructive border border-destructive/20"
                      }`}
                    >
                      {testResult.ok ? (
                        <CheckCircle2 size={13} className="mt-0.5 shrink-0" />
                      ) : (
                        <AlertCircle size={13} className="mt-0.5 shrink-0" />
                      )}
                      {testResult.text}
                    </div>
                  )}

                  <button
                    onClick={handleSendTest}
                    disabled={testing || whatsappIntegrations.length === 0}
                    className="flex items-center gap-2 justify-center bg-green-600 text-white rounded-xl py-2.5 text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-60"
                  >
                    {testing ? (
                      <Loader2 size={15} className="animate-spin" />
                    ) : (
                      <Send size={15} />
                    )}
                    {testing ? "Sending…" : "Send Test Message"}
                  </button>
                </div>
              </div>

              {/* Groq Model info */}
              <div className="bg-white rounded-2xl border border-border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Bot size={16} className="text-primary" />
                  <h2 className="font-semibold text-sm">AI Model</h2>
                </div>
                <div className="text-xs space-y-2 text-muted-foreground">
                  <div className="flex items-center justify-between bg-muted/40 rounded-xl px-4 py-3">
                    <span>Provider</span>
                    <span className="font-medium text-foreground">Groq</span>
                  </div>
                  <div className="flex items-center justify-between bg-muted/40 rounded-xl px-4 py-3">
                    <span>Model</span>
                    <span className="font-medium text-foreground font-mono">llama-3.3-70b-versatile</span>
                  </div>
                  <div className="flex items-center justify-between bg-muted/40 rounded-xl px-4 py-3">
                    <span>Context Window</span>
                    <span className="font-medium text-foreground">Last 10 messages</span>
                  </div>
                  <div className="flex items-center justify-between bg-muted/40 rounded-xl px-4 py-3">
                    <span>Max Response Tokens</span>
                    <span className="font-medium text-foreground">500</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── WEBHOOK TAB ── */}
          {activeTab === "webhook" && (
            <div className="space-y-6">
              <div className="bg-white rounded-2xl border border-border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare size={16} className="text-green-600" />
                  <h2 className="font-semibold text-sm">WhatsApp Webhook Setup</h2>
                </div>
                <p className="text-xs text-muted-foreground mb-5">
                  Enter these values in the Meta Developer Portal under your WhatsApp app →
                  Webhooks.
                </p>

                <div className="space-y-4">
                  <CopyField
                    label="Webhook URL"
                    value={webhookInfo?.webhook_url || "Loading…"}
                    copyKey="wh_url"
                    copied={copied}
                    onCopy={handleCopy}
                  />
                  <CopyField
                    label="Verify Token"
                    value={webhookInfo?.verify_token || "Loading…"}
                    copyKey="wh_token"
                    copied={copied}
                    onCopy={handleCopy}
                  />
                </div>

                <div className="mt-6 space-y-3 text-xs text-muted-foreground">
                  <h3 className="font-semibold text-foreground">Setup Steps</h3>
                  {[
                    "Go to developers.facebook.com → My Apps → your WhatsApp app",
                    "Navigate to WhatsApp → Configuration → Webhook",
                    "Click Edit, paste the Webhook URL above, paste the Verify Token above",
                    'Click Verify & Save — Meta will call your URL with hub.challenge',
                    "Subscribe to: messages, message_deliveries, message_reads",
                    "In the Channels tab, add your Phone Number ID, WABA ID & Access Token",
                  ].map((step, i) => (
                    <div key={i} className="flex gap-3">
                      <span className="w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Globe size={16} className="text-sky-600" />
                  <h2 className="font-semibold text-sm">Other Channel Webhooks</h2>
                </div>
                <div className="space-y-2 text-xs">
                  {[
                    { label: "Facebook Messenger", path: "messenger" },
                    { label: "Instagram", path: "instagram" },
                    { label: "Telegram", path: "telegram" },
                    { label: "Discord", path: "discord" },
                  ].map(({ label, path }) => {
                    const url =
                      webhookInfo?.webhook_url?.replace("whatsapp", path) ||
                      `https://wow.gpayauto.org/webhooks/${path}/`;
                    return (
                      <div
                        key={path}
                        className="flex items-center justify-between bg-muted/40 rounded-xl px-4 py-2.5"
                      >
                        <span className="text-muted-foreground">{label}</span>
                        <div className="flex items-center gap-2">
                          <code className="font-mono text-[10px]">/webhooks/{path}/</code>
                          <button
                            onClick={() => handleCopy(url, `wh_${path}`)}
                            className="hover:text-foreground text-muted-foreground"
                          >
                            {copied === `wh_${path}` ? (
                              <Check size={12} className="text-green-600" />
                            ) : (
                              <Copy size={12} />
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .inp {
          width: 100%;
          border: 1px solid hsl(var(--border));
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
          outline: none;
          background: transparent;
          transition: border-color 0.15s;
        }
        .inp:focus {
          border-color: hsl(var(--primary));
          box-shadow: 0 0 0 3px hsl(var(--primary) / 0.1);
        }
      `}</style>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      {children}
    </div>
  );
}

function SecretInput({
  value,
  placeholder,
  fieldKey,
  show,
  onToggle,
  onChange,
}: {
  value: string;
  placeholder: string;
  fieldKey: string;
  show: boolean;
  onToggle: () => void;
  onChange: (v: string) => void;
}) {
  return (
    <div className="relative">
      <input
        className="inp pr-10"
        type={show ? "text" : "password"}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete="off"
        data-key={fieldKey}
      />
      <button
        type="button"
        onClick={onToggle}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
      >
        {show ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    </div>
  );
}

function CopyField({
  label,
  value,
  copyKey,
  copied,
  onCopy,
}: {
  label: string;
  value: string;
  copyKey: string;
  copied: string | null;
  onCopy: (text: string, key: string) => void;
}) {
  return (
    <div>
      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <code className="flex-1 bg-muted/60 border border-border rounded-xl px-4 py-2.5 text-xs font-mono break-all">
          {value}
        </code>
        <button
          onClick={() => onCopy(value, copyKey)}
          className="shrink-0 flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-border bg-white hover:bg-muted text-xs font-medium transition-colors"
        >
          {copied === copyKey ? (
            <>
              <Check size={13} className="text-green-600" />
              <span className="text-green-600">Copied</span>
            </>
          ) : (
            <>
              <Copy size={13} />
              Copy
            </>
          )}
        </button>
      </div>
    </div>
  );
}
