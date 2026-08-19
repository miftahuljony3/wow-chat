"use client";

import { useState, useEffect, useCallback, useRef, DragEvent, ChangeEvent } from "react";
import Sidebar from "@/components/Sidebar";
import { automationApi, channelsApi } from "@/lib/api";
import {
  CalendarClock, Upload, Image as ImageIcon, Video, Trash2, RotateCcw,
  Play, CheckCircle2, XCircle, AlertCircle, Loader2, ChevronDown,
  ChevronUp, Plus, Zap, BarChart2, RefreshCw, Clock, Shield,
  MessageSquare, Bot, FileText, Filter, X,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AutoPostConfig {
  id: string;
  integration: string;
  integration_display: string;
  is_auto_post_enabled: boolean;
  post_time: string;
  niche_keywords: string;
  custom_caption_prompt: string;
  last_post_date: string | null;
  total_posts_published: number;
  spam_deletion_enabled: boolean;
  auto_reply_enabled: boolean;
  moderation_prompt: string;
  reply_persona: string;
  business_context: string;
  reply_language: string;
  like_valid_comments: boolean;
  reply_only_to_questions: boolean;
  total_replies_sent: number;
  reply_rules: ReplyRule[];
  media_unused_count: number;
}

interface ReplyRule {
  id: string;
  config: string;
  name: string;
  keywords: string;
  match_type: "any" | "all" | "exact";
  reply_text: string;
  is_active: boolean;
  priority: number;
  times_triggered: number;
  created_at: string;
}

interface CloudMedia {
  id: string;
  file_name: string;
  media_type: "image" | "video";
  file_url: string;
  is_used: boolean;
  used_at: string | null;
  used_in_post_id: string;
  created_at: string;
}

interface PostLog {
  id: string;
  status: "success" | "failed" | "no_media";
  fb_post_id: string;
  caption_used: string;
  media_file: { id: string; file_name: string } | null;
  error_message: string;
  created_at: string;
}

interface ModerationLog {
  id: string;
  author_name: string;
  comment_text: string;
  ai_verdict: "spam" | "abusive" | "valid";
  ai_reply: string;
  action: "deleted" | "replied" | "ignored" | "error";
  created_at: string;
}

interface Integration {
  id: string;
  platform: string;
  display_name: string;
  page_id: string;
}

// ─── Default create form ──────────────────────────────────────────────────────

const DEFAULT_FORM = {
  integration: "",
  is_auto_post_enabled: false,
  post_time: "09:00",
  niche_keywords: "",
  custom_caption_prompt: "",
  spam_deletion_enabled: true,
  auto_reply_enabled: true,
  moderation_prompt: "",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AutomationPage() {
  const [tab, setTab] = useState<"autopost" | "media" | "activity">("autopost");

  const [configs, setConfigs] = useState<AutoPostConfig[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [media, setMedia] = useState<CloudMedia[]>([]);
  const [mediaFilter, setMediaFilter] = useState<"all" | "unused" | "used">("all");
  const [selectedConfig, setSelectedConfig] = useState<string>("");
  const [postLogs, setPostLogs] = useState<PostLog[]>([]);
  const [modLogs, setModLogs] = useState<ModerationLog[]>([]);
  const [activityTab, setActivityTab] = useState<"posts" | "moderation">("posts");

  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [triggeringId, setTriggeringId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState(DEFAULT_FORM);
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Load ──────────────────────────────────────────────────────────────────

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cfgRes, intRes, medRes] = await Promise.all([
        automationApi.listConfigs().catch(() => ({ data: [] })),
        channelsApi.list().catch(() => ({ data: [] })),
        automationApi.listMedia().catch(() => ({ data: [] })),
      ]);
      const cfgList: AutoPostConfig[] = cfgRes.data.results ?? cfgRes.data;
      setConfigs(cfgList);
      setIntegrations(
        (intRes.data.results ?? intRes.data).filter(
          (i: Integration) => i.platform === "messenger" || i.platform === "instagram"
        )
      );
      setMedia(medRes.data.results ?? medRes.data);
      if (cfgList.length > 0 && !selectedConfig) {
        setSelectedConfig(cfgList[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedConfig]);

  useEffect(() => {
    loadAll();
  }, []);// eslint-disable-line react-hooks/exhaustive-deps

  // Load activity logs when tab or config changes
  useEffect(() => {
    if (tab !== "activity" || !selectedConfig) return;
    automationApi.postLogs(selectedConfig).then((r) => setPostLogs(r.data));
    automationApi.moderationLogs(selectedConfig).then((r) => setModLogs(r.data));
  }, [tab, selectedConfig]);

  // ── Toast ────────────────────────────────────────────────────────────────

  const showToast = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  // ── Toggle enable/disable ─────────────────────────────────────────────────

  const toggleEnabled = async (cfg: AutoPostConfig) => {
    setSavingId(cfg.id);
    try {
      await automationApi.updateConfig(cfg.id, {
        is_auto_post_enabled: !cfg.is_auto_post_enabled,
      });
      setConfigs((prev) =>
        prev.map((c) =>
          c.id === cfg.id
            ? { ...c, is_auto_post_enabled: !c.is_auto_post_enabled }
            : c
        )
      );
      showToast(
        `Auto-posting ${!cfg.is_auto_post_enabled ? "enabled" : "disabled"} for ${cfg.integration_display}.`
      );
    } catch {
      showToast("Failed to update.", false);
    } finally {
      setSavingId(null);
    }
  };

  // ── Inline field update ────────────────────────────────────────────────────

  const updateField = async (id: string, field: string, value: unknown) => {
    setSavingId(id);
    try {
      const payload =
        field === "__batch__"
          ? (value as Record<string, unknown>)
          : { [field]: value };
      const res = await automationApi.updateConfig(id, payload);
      setConfigs((prev) => prev.map((c) => (c.id === id ? { ...c, ...res.data } : c)));
      showToast("Saved.");
    } catch {
      showToast("Save failed.", false);
    } finally {
      setSavingId(null);
    }
  };

  // ── Trigger now ────────────────────────────────────────────────────────────

  const triggerNow = async (id: string) => {
    setTriggeringId(id);
    try {
      await automationApi.triggerNow(id);
      showToast("Post task queued — check Activity tab in a moment.");
    } catch {
      showToast("Failed to trigger post.", false);
    } finally {
      setTriggeringId(null);
    }
  };

  // ── Create config ─────────────────────────────────────────────────────────

  const createConfig = async () => {
    if (!createForm.integration) {
      showToast("Select a Facebook/Instagram integration.", false);
      return;
    }
    setCreating(true);
    try {
      const res = await automationApi.createConfig(createForm);
      setConfigs((prev) => [res.data, ...prev]);
      setCreateForm(DEFAULT_FORM);
      setShowCreateForm(false);
      showToast("Config created.");
    } catch {
      showToast("Failed to create config.", false);
    } finally {
      setCreating(false);
    }
  };

  // ── Media upload ──────────────────────────────────────────────────────────

  const uploadFiles = async (files: FileList | File[]) => {
    const arr = Array.from(files);
    for (const file of arr) {
      const key = `${file.name}-${Date.now()}`;
      setUploadProgress((p) => ({ ...p, [key]: 0 }));
      try {
        const res = await automationApi.uploadMedia(file);
        setMedia((prev) => [res.data, ...prev]);
        setUploadProgress((p) => {
          const n = { ...p };
          delete n[key];
          return n;
        });
        showToast(`${file.name} uploaded.`);
      } catch {
        setUploadProgress((p) => {
          const n = { ...p };
          delete n[key];
          return n;
        });
        showToast(`Failed to upload ${file.name}.`, false);
      }
    }
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
  };

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) uploadFiles(e.target.files);
    e.target.value = "";
  };

  const deleteMedia = async (id: string) => {
    if (!confirm("Delete this file?")) return;
    await automationApi.deleteMedia(id);
    setMedia((prev) => prev.filter((m) => m.id !== id));
    showToast("File deleted.");
  };

  const markUnused = async (id: string) => {
    await automationApi.markUnused(id);
    setMedia((prev) => prev.map((m) => m.id === id ? { ...m, is_used: false, used_at: null } : m));
    showToast("Marked as unused.");
  };

  // ── Derived ────────────────────────────────────────────────────────────────

  const usedIntegrationIds = new Set(configs.map((c) => c.integration));
  const availableIntegrations = integrations.filter((i) => !usedIntegrationIds.has(i.id));

  const filteredMedia = media.filter((m) => {
    if (mediaFilter === "unused") return !m.is_used;
    if (mediaFilter === "used") return m.is_used;
    return true;
  });

  const unusedCount = media.filter((m) => !m.is_used).length;
  const uploadCount = Object.keys(uploadProgress).length;

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen bg-[#f5f6fa] overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* ── Header ────────────────────────────────────────────────────── */}
        <div className="bg-white border-b border-border px-8 py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <CalendarClock size={18} className="text-primary" />
            </div>
            <div>
              <h1 className="text-base font-bold leading-tight">Automation</h1>
              <p className="text-xs text-muted-foreground">
                Daily page posting · AI comment moderation · Media library
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadAll}
              className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground"
              title="Refresh"
            >
              <RefreshCw size={15} />
            </button>
            {tab === "autopost" && availableIntegrations.length > 0 && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90"
              >
                <Plus size={14} /> New Config
              </button>
            )}
          </div>
        </div>

        {/* ── Stats bar ──────────────────────────────────────────────────── */}
        {!loading && configs.length > 0 && (
          <div className="bg-white border-b border-border px-8 py-3 flex gap-6 shrink-0">
            <Stat label="Active configs" value={configs.filter((c) => c.is_auto_post_enabled).length} icon="🟢" />
            <Stat label="Total posts" value={configs.reduce((a, c) => a + c.total_posts_published, 0)} icon="📤" />
            <Stat label="Media unused" value={unusedCount} icon="🖼️" />
            <Stat label="Media total" value={media.length} icon="📁" />
          </div>
        )}

        {/* ── Tabs ───────────────────────────────────────────────────────── */}
        <div className="bg-white border-b border-border px-8 flex gap-1 shrink-0">
          {(["autopost", "media", "activity"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "autopost" ? "⚡ Auto-Post" : t === "media" ? "🖼️ Media Library" : "📊 Activity"}
            </button>
          ))}
        </div>

        {/* ── Content ───────────────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-8">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-muted-foreground gap-2">
              <Loader2 size={20} className="animate-spin" /> Loading…
            </div>
          ) : (
            <>
              {/* ════ AUTO-POST TAB ════════════════════════════════════════ */}
              {tab === "autopost" && (
                <div className="max-w-3xl mx-auto space-y-4">
                  {/* Create form (slide-in card) */}
                  {showCreateForm && (
                    <div className="bg-white rounded-2xl border border-primary/30 shadow-sm overflow-hidden">
                      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                        <h2 className="font-semibold text-sm flex items-center gap-2">
                          <Plus size={15} className="text-primary" /> New Auto-Post Config
                        </h2>
                        <button onClick={() => setShowCreateForm(false)} className="text-muted-foreground hover:text-foreground">
                          <X size={16} />
                        </button>
                      </div>
                      <div className="p-6 space-y-4">
                        <Fld label="Facebook / Instagram Integration">
                          <select
                            className="inp"
                            value={createForm.integration}
                            onChange={(e) => setCreateForm({ ...createForm, integration: e.target.value })}
                          >
                            <option value="">— select page —</option>
                            {availableIntegrations.map((i) => (
                              <option key={i.id} value={i.id}>
                                {i.display_name || i.page_id} ({i.platform})
                              </option>
                            ))}
                          </select>
                          {availableIntegrations.length === 0 && (
                            <p className="text-xs text-amber-600 mt-1">
                              All FB/Instagram integrations already have a config, or none are connected yet.
                            </p>
                          )}
                        </Fld>

                        <div className="grid grid-cols-2 gap-4">
                          <Fld label="Daily Post Time (UTC)">
                            <input
                              type="time"
                              className="inp"
                              value={createForm.post_time}
                              onChange={(e) => setCreateForm({ ...createForm, post_time: e.target.value })}
                            />
                          </Fld>
                          <Fld label="Niche Keywords">
                            <input
                              className="inp"
                              placeholder="fitness, wellness, gym"
                              value={createForm.niche_keywords}
                              onChange={(e) => setCreateForm({ ...createForm, niche_keywords: e.target.value })}
                            />
                          </Fld>
                        </div>

                        <div className="flex gap-6 py-1">
                          <Toggle
                            label="Enable auto-posting"
                            value={createForm.is_auto_post_enabled}
                            onChange={(v) => setCreateForm({ ...createForm, is_auto_post_enabled: v })}
                          />
                          <Toggle
                            label="Delete spam comments"
                            value={createForm.spam_deletion_enabled}
                            onChange={(v) => setCreateForm({ ...createForm, spam_deletion_enabled: v })}
                          />
                          <Toggle
                            label="Auto-reply to comments"
                            value={createForm.auto_reply_enabled}
                            onChange={(v) => setCreateForm({ ...createForm, auto_reply_enabled: v })}
                          />
                        </div>

                        <button
                          onClick={createConfig}
                          disabled={creating || !createForm.integration}
                          className="flex items-center gap-2 justify-center w-full bg-primary text-white rounded-xl py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-60"
                        >
                          {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                          {creating ? "Creating…" : "Create Config"}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Empty state */}
                  {configs.length === 0 && !showCreateForm && (
                    <EmptyState
                      icon="⚡"
                      title="No auto-post configs yet"
                      subtitle="Auto-Post requires a Facebook Page or Instagram account connected via Settings → Channels. Once connected, create a config here to start daily AI-generated posting."
                      action={
                        availableIntegrations.length > 0 ? (
                          <button
                            onClick={() => setShowCreateForm(true)}
                            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl text-sm font-medium hover:bg-primary/90"
                          >
                            <Plus size={14} /> Create First Config
                          </button>
                        ) : (
                          <div className="flex flex-col items-center gap-2">
                            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5 max-w-sm text-center leading-relaxed">
                              📘 Go to <strong>Settings → Channels</strong> and add a{" "}
                              <strong>Facebook Messenger</strong> or <strong>Instagram</strong>{" "}
                              integration to unlock auto-posting.
                            </p>
                            <p className="text-[11px] text-muted-foreground">
                              Web Chat widget is always-on and doesn&apos;t need a config here.
                            </p>
                          </div>
                        )
                      }
                    />
                  )}

                  {/* Config cards */}
                  {configs.map((cfg) => (
                    <ConfigCard
                      key={cfg.id}
                      cfg={cfg}
                      expanded={expandedId === cfg.id}
                      saving={savingId === cfg.id}
                      triggering={triggeringId === cfg.id}
                      unusedMediaCount={unusedCount}
                      onToggle={() => setExpandedId(expandedId === cfg.id ? null : cfg.id)}
                      onEnableToggle={() => toggleEnabled(cfg)}
                      onTrigger={() => triggerNow(cfg.id)}
                      onUpdate={(field, val) => updateField(cfg.id, field, val)}
                      onDelete={async () => {
                        if (!confirm("Delete this config?")) return;
                        await automationApi.deleteConfig(cfg.id);
                        setConfigs((prev) => prev.filter((c) => c.id !== cfg.id));
                        showToast("Config deleted.");
                      }}
                      onGoToMedia={() => setTab("media")}
                      onRulesChanged={loadAll}
                    />
                  ))}
                </div>
              )}

              {/* ════ MEDIA LIBRARY TAB ════════════════════════════════════ */}
              {tab === "media" && (
                <div className="max-w-5xl mx-auto space-y-6">
                  {/* Upload zone */}
                  <div
                    onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={onDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-colors ${
                      dragging
                        ? "border-primary bg-primary/5"
                        : "border-border bg-white hover:border-primary/50 hover:bg-primary/2"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept="image/*,video/*"
                      className="hidden"
                      onChange={onFileChange}
                    />
                    <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-3">
                      <Upload size={22} className="text-primary" />
                    </div>
                    <p className="font-medium text-sm">
                      {dragging ? "Drop files here" : "Drag & drop images or videos"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      or click to browse · JPG, PNG, GIF, MP4, MOV · No size limit
                    </p>
                    {uploadCount > 0 && (
                      <div className="flex items-center gap-2 justify-center mt-3 text-xs text-primary">
                        <Loader2 size={12} className="animate-spin" />
                        Uploading {uploadCount} file{uploadCount > 1 ? "s" : ""}…
                      </div>
                    )}
                  </div>

                  {/* Filter + stats bar */}
                  <div className="flex items-center justify-between">
                    <div className="flex gap-1 bg-white rounded-xl border border-border p-1">
                      {(["all", "unused", "used"] as const).map((f) => (
                        <button
                          key={f}
                          onClick={() => setMediaFilter(f)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                            mediaFilter === f
                              ? "bg-primary text-white"
                              : "text-muted-foreground hover:bg-muted"
                          }`}
                        >
                          {f}{" "}
                          {f === "all" ? `(${media.length})` :
                           f === "unused" ? `(${unusedCount})` :
                           `(${media.length - unusedCount})`}
                        </button>
                      ))}
                    </div>
                    {media.some((m) => m.is_used) && (
                      <button
                        onClick={async () => {
                          await automationApi.bulkMarkUnused();
                          setMedia((prev) => prev.map((m) => ({ ...m, is_used: false, used_at: null })));
                          showToast("All files reset to unused.");
                        }}
                        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-lg border border-border bg-white hover:bg-muted"
                      >
                        <RotateCcw size={12} /> Reset all to unused
                      </button>
                    )}
                  </div>

                  {/* Grid */}
                  {filteredMedia.length === 0 ? (
                    <EmptyState
                      icon="🖼️"
                      title="No files here"
                      subtitle={
                        mediaFilter === "unused"
                          ? "All your media has been used. Upload more or reset used files."
                          : "Upload images and videos to start auto-posting."
                      }
                    />
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-3">
                      {filteredMedia.map((m) => (
                        <MediaCard
                          key={m.id}
                          media={m}
                          onDelete={() => deleteMedia(m.id)}
                          onMarkUnused={() => markUnused(m.id)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ════ ACTIVITY TAB ═════════════════════════════════════════ */}
              {tab === "activity" && (
                <div className="max-w-4xl mx-auto space-y-5">
                  {/* Config selector */}
                  {configs.length > 1 && (
                    <div className="flex items-center gap-3">
                      <Filter size={14} className="text-muted-foreground" />
                      <select
                        className="text-sm border border-border rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:border-primary"
                        value={selectedConfig}
                        onChange={(e) => setSelectedConfig(e.target.value)}
                      >
                        {configs.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.integration_display}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {configs.length === 0 ? (
                    <EmptyState icon="📊" title="No activity yet" subtitle="Create an auto-post config to start seeing logs here." />
                  ) : (
                    <>
                      {/* Sub-tabs */}
                      <div className="flex gap-1 bg-white rounded-xl border border-border p-1 w-fit">
                        <button
                          onClick={() => setActivityTab("posts")}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                            activityTab === "posts" ? "bg-primary text-white" : "text-muted-foreground hover:bg-muted"
                          }`}
                        >
                          <FileText size={12} /> Post History ({postLogs.length})
                        </button>
                        <button
                          onClick={() => setActivityTab("moderation")}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                            activityTab === "moderation" ? "bg-primary text-white" : "text-muted-foreground hover:bg-muted"
                          }`}
                        >
                          <Shield size={12} /> Moderation ({modLogs.length})
                        </button>
                      </div>

                      {/* Post logs */}
                      {activityTab === "posts" && (
                        <div className="space-y-2">
                          {postLogs.length === 0 ? (
                            <EmptyState icon="📤" title="No posts yet" subtitle="Auto-posts will appear here after the first scheduled run." />
                          ) : (
                            postLogs.map((log) => <PostLogRow key={log.id} log={log} />)
                          )}
                        </div>
                      )}

                      {/* Moderation logs */}
                      {activityTab === "moderation" && (
                        <div className="space-y-2">
                          {modLogs.length === 0 ? (
                            <EmptyState icon="🛡️" title="No moderation logs" subtitle="Comment events will appear here once the webhook is receiving Facebook feed events." />
                          ) : (
                            modLogs.map((log) => <ModerationLogRow key={log.id} log={log} />)
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── Toast ───────────────────────────────────────────────────────────── */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-medium z-50 transition-all ${
            toast.ok ? "bg-green-600 text-white" : "bg-red-600 text-white"
          }`}
        >
          {toast.ok ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
          {toast.msg}
        </div>
      )}

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

function Stat({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-lg leading-none">{icon}</span>
      <div>
        <p className="text-base font-bold leading-none">{value}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5">{label}</p>
      </div>
    </div>
  );
}

function Fld({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      {children}
    </div>
  );
}

function Toggle({
  label, value, onChange,
}: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <div
        onClick={() => onChange(!value)}
        className={`w-9 h-5 rounded-full transition-colors relative shrink-0 ${value ? "bg-primary" : "bg-muted-foreground/30"}`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${value ? "translate-x-4" : ""}`}
        />
      </div>
      <span className="text-xs text-muted-foreground">{label}</span>
    </label>
  );
}

// ── Config Card ───────────────────────────────────────────────────────────────

function ConfigCard({
  cfg, expanded, saving, triggering, unusedMediaCount,
  onToggle, onEnableToggle, onTrigger, onUpdate, onDelete, onGoToMedia, onRulesChanged,
}: {
  cfg: AutoPostConfig;
  expanded: boolean;
  saving: boolean;
  triggering: boolean;
  unusedMediaCount: number;
  onToggle: () => void;
  onEnableToggle: () => void;
  onTrigger: () => void;
  onUpdate: (field: string, value: unknown) => void;
  onDelete: () => void;
  onGoToMedia: () => void;
  onRulesChanged: () => void;
}) {
  const snapshot = (c: AutoPostConfig) => ({
    post_time: c.post_time,
    niche_keywords: c.niche_keywords,
    custom_caption_prompt: c.custom_caption_prompt,
    spam_deletion_enabled: c.spam_deletion_enabled,
    auto_reply_enabled: c.auto_reply_enabled,
    moderation_prompt: c.moderation_prompt,
    reply_persona: c.reply_persona ?? "",
    business_context: c.business_context ?? "",
    reply_language: c.reply_language ?? "auto",
    like_valid_comments: c.like_valid_comments ?? false,
    reply_only_to_questions: c.reply_only_to_questions ?? false,
  });
  const [local, setLocal] = useState(() => snapshot(cfg));

  // Sync when cfg changes (after save)
  useEffect(() => {
    setLocal(snapshot(cfg));
  }, [cfg]);// eslint-disable-line react-hooks/exhaustive-deps

  const saveAll = () => onUpdate("__batch__", local);

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      {/* Header row */}
      <div className="flex items-center gap-4 px-5 py-4">
        {/* Platform icon */}
        <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0 text-xl">
          📘
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm truncate">{cfg.integration_display}</p>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><Clock size={11} /> {cfg.post_time} UTC</span>
            <span className="flex items-center gap-1"><FileText size={11} /> {cfg.total_posts_published} posts</span>
            <span className="flex items-center gap-1">
              <ImageIcon size={11} /> {unusedMediaCount} unused
            </span>
            {cfg.last_post_date && (
              <span>Last: {new Date(cfg.last_post_date).toLocaleDateString()}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Enable toggle */}
          <div
            onClick={onEnableToggle}
            className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${
              cfg.is_auto_post_enabled ? "bg-green-500" : "bg-muted-foreground/30"
            }`}
          >
            {saving ? (
              <Loader2 size={12} className="absolute top-1 left-1 text-white animate-spin" />
            ) : (
              <span
                className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                  cfg.is_auto_post_enabled ? "translate-x-5" : ""
                }`}
              />
            )}
          </div>
          <span className={`text-xs font-medium ${cfg.is_auto_post_enabled ? "text-green-600" : "text-muted-foreground"}`}>
            {cfg.is_auto_post_enabled ? "Active" : "Paused"}
          </span>

          {/* Trigger now */}
          <button
            onClick={onTrigger}
            disabled={triggering || unusedMediaCount === 0}
            title={unusedMediaCount === 0 ? "Upload media first" : "Post now"}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {triggering ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
            Post Now
          </button>

          {/* Expand */}
          <button onClick={onToggle} className="text-muted-foreground hover:text-foreground p-1.5 rounded-lg hover:bg-muted">
            {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>

          {/* Delete */}
          <button onClick={onDelete} className="text-destructive/60 hover:text-destructive p-1.5 rounded-lg hover:bg-destructive/10">
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {/* No-media warning banner */}
      {unusedMediaCount === 0 && (
        <div className="mx-5 mb-4 -mt-1 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5">
          <AlertCircle size={15} className="text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-800 leading-relaxed">
            <strong>Nothing will post — the Media Library is empty.</strong> Auto-Post picks an
            unused image/video, writes an AI caption, and publishes it. Upload at least one file in
            the{" "}
            <button
              onClick={onGoToMedia}
              className="underline font-semibold hover:text-amber-900"
            >
              Media Library
            </button>{" "}
            tab first.
          </div>
        </div>
      )}

      {/* Expanded settings */}
      {expanded && (
        <div className="border-t border-border px-5 py-5 space-y-5 bg-muted/20">
          {/* ── Auto-posting settings ──────────────────────────────────── */}
          <Section title="Auto-Posting" icon={<CalendarClock size={14} className="text-primary" />}>
            <div className="grid grid-cols-2 gap-4">
              <Fld label="Daily Post Time (UTC)">
                <input
                  type="time"
                  className="inp"
                  value={local.post_time}
                  onChange={(e) => setLocal({ ...local, post_time: e.target.value })}
                />
              </Fld>
              <Fld label="Niche / Topic Keywords">
                <input
                  className="inp"
                  placeholder="fitness, nutrition, mindfulness"
                  value={local.niche_keywords}
                  onChange={(e) => setLocal({ ...local, niche_keywords: e.target.value })}
                />
              </Fld>
            </div>
            <Fld label="Custom Caption Prompt (optional — leave blank for default AI prompt)">
              <textarea
                className="inp min-h-[80px] resize-none text-xs font-mono"
                placeholder={`You are a creative social media manager for a [niche] page...\nReturn ONLY the caption.`}
                value={local.custom_caption_prompt}
                onChange={(e) => setLocal({ ...local, custom_caption_prompt: e.target.value })}
              />
            </Fld>
          </Section>

          {/* ── Comment moderation ─────────────────────────────────────── */}
          <Section title="Comment Moderation" icon={<Shield size={14} className="text-primary" />}>
            <div className="flex gap-6 py-1">
              <Toggle
                label="Delete spam & abusive comments"
                value={local.spam_deletion_enabled}
                onChange={(v) => setLocal({ ...local, spam_deletion_enabled: v })}
              />
              <Toggle
                label="Auto-reply to valid comments"
                value={local.auto_reply_enabled}
                onChange={(v) => setLocal({ ...local, auto_reply_enabled: v })}
              />
            </div>
            <Fld label="Additional Moderation Context (optional)">
              <textarea
                className="inp min-h-[60px] resize-none"
                placeholder="e.g. Ignore comments that mention competitor names. Treat Spanish comments as valid."
                value={local.moderation_prompt}
                onChange={(e) => setLocal({ ...local, moderation_prompt: e.target.value })}
              />
            </Fld>
          </Section>

          {/* ── AI Auto-Reply ──────────────────────────────────────────── */}
          <Section title="AI Auto-Reply" icon={<MessageSquare size={14} className="text-primary" />}>
            <div className="grid grid-cols-2 gap-4">
              <Fld label="Reply Language">
                <select
                  className="inp"
                  value={local.reply_language}
                  onChange={(e) => setLocal({ ...local, reply_language: e.target.value })}
                >
                  <option value="auto">Match commenter&apos;s language</option>
                  <option value="en">English</option>
                  <option value="bn">Bengali</option>
                  <option value="hi">Hindi</option>
                  <option value="ar">Arabic</option>
                  <option value="es">Spanish</option>
                </select>
              </Fld>
              <div className="flex flex-col justify-center gap-2 pt-4">
                <Toggle
                  label="Like valid comments 👍"
                  value={local.like_valid_comments}
                  onChange={(v) => setLocal({ ...local, like_valid_comments: v })}
                />
                <Toggle
                  label="Only reply to questions"
                  value={local.reply_only_to_questions}
                  onChange={(v) => setLocal({ ...local, reply_only_to_questions: v })}
                />
              </div>
            </div>
            <Fld label="Reply Persona / Tone (optional)">
              <input
                className="inp"
                placeholder="e.g. friendly and upbeat, thank the person, add one emoji"
                value={local.reply_persona}
                onChange={(e) => setLocal({ ...local, reply_persona: e.target.value })}
              />
            </Fld>
            <Fld label="Business Info the AI can use to answer (optional)">
              <textarea
                className="inp min-h-[70px] resize-none"
                placeholder={"Hours: 9am–9pm daily\nDelivery: 2–3 days, free over ৳1000\nLocation: Dhaka\nPrice list / FAQs…"}
                value={local.business_context}
                onChange={(e) => setLocal({ ...local, business_context: e.target.value })}
              />
            </Fld>
          </Section>

          <button
            onClick={saveAll}
            disabled={saving}
            className="flex items-center gap-2 justify-center w-full bg-primary text-white rounded-xl py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-60"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
            {saving ? "Saving…" : "Save Settings"}
          </button>

          {/* ── Keyword Auto-Reply Rules ───────────────────────────────── */}
          <ReplyRulesManager
            configId={cfg.id}
            rules={cfg.reply_rules || []}
            totalReplies={cfg.total_replies_sent}
            onChanged={onRulesChanged}
          />
        </div>
      )}
    </div>
  );
}

// ── Reply Rules Manager ───────────────────────────────────────────────────────

function ReplyRulesManager({
  configId, rules, totalReplies, onChanged,
}: {
  configId: string;
  rules: ReplyRule[];
  totalReplies: number;
  onChanged: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    name: "", keywords: "", match_type: "any", reply_text: "",
  });

  const addRule = async () => {
    if (!form.keywords.trim() || !form.reply_text.trim()) return;
    setBusy(true);
    try {
      await automationApi.createRule({ ...form, config: configId, is_active: true });
      setForm({ name: "", keywords: "", match_type: "any", reply_text: "" });
      setAdding(false);
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const toggleRule = async (r: ReplyRule) => {
    await automationApi.updateRule(r.id, { is_active: !r.is_active });
    onChanged();
  };

  const removeRule = async (r: ReplyRule) => {
    if (!confirm("Delete this rule?")) return;
    await automationApi.deleteRule(r.id);
    onChanged();
  };

  return (
    <div className="border border-border rounded-2xl bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          <Zap size={14} className="text-primary" /> Keyword Auto-Reply Rules
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-muted-foreground">{totalReplies} replies sent</span>
          <button
            onClick={() => setAdding((a) => !a)}
            className="flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80"
          >
            <Plus size={13} /> Add Rule
          </button>
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground leading-relaxed">
        Instant canned replies for common keywords — checked <strong>before</strong> the AI.
        First matching active rule wins (e.g. keyword <code>price</code> → your price reply).
      </p>

      {/* Add form */}
      {adding && (
        <div className="bg-muted/40 rounded-xl p-3 space-y-2.5">
          <div className="grid grid-cols-2 gap-2">
            <input
              className="inp text-xs"
              placeholder="Rule name (optional)"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <select
              className="inp text-xs"
              value={form.match_type}
              onChange={(e) => setForm({ ...form, match_type: e.target.value })}
            >
              <option value="any">Match ANY keyword</option>
              <option value="all">Match ALL keywords</option>
              <option value="exact">Exact phrase</option>
            </select>
          </div>
          <input
            className="inp text-xs"
            placeholder="Keywords, comma-separated: price, cost, how much"
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
          />
          <textarea
            className="inp text-xs min-h-[56px] resize-none"
            placeholder="Reply to send, e.g. Thanks for asking! Our prices start at ৳500. DM us for details 😊"
            value={form.reply_text}
            onChange={(e) => setForm({ ...form, reply_text: e.target.value })}
          />
          <div className="flex gap-2">
            <button
              onClick={addRule}
              disabled={busy || !form.keywords.trim() || !form.reply_text.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
            >
              {busy ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
              Save Rule
            </button>
            <button
              onClick={() => setAdding(false)}
              className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Rules list */}
      {rules.length === 0 ? (
        <p className="text-[11px] text-muted-foreground italic py-1">
          No rules yet — every valid comment goes to the AI.
        </p>
      ) : (
        <div className="space-y-1.5">
          {rules.map((r) => (
            <div
              key={r.id}
              className={`flex items-start gap-3 rounded-xl border px-3 py-2 ${
                r.is_active ? "border-border bg-white" : "border-border bg-muted/30 opacity-60"
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-semibold">{r.name || "Rule"}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">
                    {r.match_type}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {r.times_triggered}× triggered
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
                  <span className="font-mono">{r.keywords}</span> → {r.reply_text}
                </p>
              </div>
              <button
                onClick={() => toggleRule(r)}
                title={r.is_active ? "Disable" : "Enable"}
                className={`text-[10px] font-medium px-2 py-1 rounded-lg shrink-0 ${
                  r.is_active ? "text-green-600 bg-green-50" : "text-muted-foreground bg-muted"
                }`}
              >
                {r.is_active ? "Active" : "Off"}
              </button>
              <button
                onClick={() => removeRule(r)}
                className="text-destructive/60 hover:text-destructive p-1 shrink-0"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ConfigCard calls onUpdate("__batch__", local) — handle it in parent by patching all fields
// We intercept in the page-level updateField by detecting __batch__:

// ── MediaCard ─────────────────────────────────────────────────────────────────

function MediaCard({
  media, onDelete, onMarkUnused,
}: {
  media: CloudMedia;
  onDelete: () => void;
  onMarkUnused: () => void;
}) {
  const [hover, setHover] = useState(false);
  const isImg = media.media_type === "image";

  return (
    <div
      className="relative group rounded-xl overflow-hidden border border-border bg-white aspect-square"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* Thumbnail */}
      {isImg ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={media.file_url}
          alt={media.file_name}
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center bg-muted gap-2">
          <Video size={28} className="text-muted-foreground" />
          <span className="text-[10px] text-muted-foreground text-center px-2 truncate w-full text-center">
            {media.file_name}
          </span>
        </div>
      )}

      {/* Used overlay */}
      {media.is_used && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
          <span className="bg-white/20 text-white text-[10px] font-semibold px-2 py-0.5 rounded-full">
            USED
          </span>
        </div>
      )}

      {/* Hover actions */}
      {hover && (
        <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center gap-2">
          {media.is_used && (
            <button
              onClick={onMarkUnused}
              className="flex items-center gap-1 text-[11px] bg-white/20 hover:bg-white/30 text-white px-2.5 py-1 rounded-lg"
            >
              <RotateCcw size={11} /> Reset
            </button>
          )}
          <button
            onClick={onDelete}
            className="flex items-center gap-1 text-[11px] bg-red-500/80 hover:bg-red-600 text-white px-2.5 py-1 rounded-lg"
          >
            <Trash2 size={11} /> Delete
          </button>
        </div>
      )}

      {/* Bottom label */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent px-2 pt-4 pb-1">
        <p className="text-[10px] text-white truncate">{media.file_name}</p>
        <p className="text-[9px] text-white/60">
          {new Date(media.created_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
}

// ── PostLogRow ────────────────────────────────────────────────────────────────

function PostLogRow({ log }: { log: PostLog }) {
  const [open, setOpen] = useState(false);
  const statusIcon = {
    success: <CheckCircle2 size={14} className="text-green-600" />,
    failed: <XCircle size={14} className="text-red-500" />,
    no_media: <AlertCircle size={14} className="text-amber-500" />,
  }[log.status];

  const statusColor = {
    success: "bg-green-50 border-green-200",
    failed: "bg-red-50 border-red-200",
    no_media: "bg-amber-50 border-amber-200",
  }[log.status];

  return (
    <div className={`rounded-xl border p-4 ${statusColor}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {statusIcon}
          <span className="text-sm font-medium capitalize">{log.status.replace("_", " ")}</span>
          {log.fb_post_id && (
            <span className="text-xs text-muted-foreground font-mono">#{log.fb_post_id}</span>
          )}
          {log.media_file && (
            <span className="text-xs text-muted-foreground">· {log.media_file.file_name}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {new Date(log.created_at).toLocaleString()}
          </span>
          {log.caption_used && (
            <button onClick={() => setOpen(!open)} className="text-muted-foreground hover:text-foreground">
              {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
        </div>
      </div>
      {open && log.caption_used && (
        <div className="mt-3 text-xs text-muted-foreground bg-white/60 rounded-lg px-3 py-2 leading-relaxed">
          {log.caption_used}
        </div>
      )}
      {log.error_message && (
        <p className="mt-2 text-xs text-red-600">{log.error_message}</p>
      )}
    </div>
  );
}

// ── ModerationLogRow ──────────────────────────────────────────────────────────

function ModerationLogRow({ log }: { log: ModerationLog }) {
  const [open, setOpen] = useState(false);
  const verdictColor = {
    spam: "text-amber-600 bg-amber-50",
    abusive: "text-red-600 bg-red-50",
    valid: "text-green-700 bg-green-50",
  }[log.ai_verdict];

  const actionColor = {
    deleted: "text-red-600",
    replied: "text-green-700",
    ignored: "text-muted-foreground",
    error: "text-red-600",
  }[log.action];

  return (
    <div className="bg-white rounded-xl border border-border p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-medium text-sm">{log.author_name || "Anonymous"}</span>
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${verdictColor}`}>
              {log.ai_verdict.toUpperCase()}
            </span>
            <span className={`text-xs font-medium ${actionColor}`}>→ {log.action}</span>
          </div>
          <p className="text-xs text-muted-foreground truncate">{log.comment_text}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] text-muted-foreground whitespace-nowrap">
            {new Date(log.created_at).toLocaleString()}
          </span>
          {log.ai_reply && (
            <button onClick={() => setOpen(!open)} className="text-muted-foreground hover:text-foreground">
              {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
        </div>
      </div>
      {open && log.ai_reply && (
        <div className="mt-3 text-xs bg-green-50 border border-green-100 rounded-lg px-3 py-2 text-green-800 leading-relaxed">
          <span className="font-semibold">AI reply: </span>{log.ai_reply}
        </div>
      )}
    </div>
  );
}

// ── Section ───────────────────────────────────────────────────────────────────

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {icon} {title}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────

function EmptyState({
  icon, title, subtitle, action,
}: {
  icon: string;
  title: string;
  subtitle: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
      <span className="text-4xl">{icon}</span>
      <p className="font-semibold text-sm">{title}</p>
      <p className="text-xs text-muted-foreground max-w-xs">{subtitle}</p>
      {action}
    </div>
  );
}
