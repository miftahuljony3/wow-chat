"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { Zap } from "lucide-react";

export default function RegisterPage() {
  const [form, setForm] = useState({
    username: "", email: "", password: "",
    first_name: "", last_name: "", workspace_name: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authApi.register(form);
      router.push("/login?registered=1");
    } catch (err: unknown) {
      const e = err as { response?: { data?: Record<string, string[]> } };
      const detail = Object.values(e?.response?.data || {}).flat().join(" ");
      setError(detail || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#16213e]">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-sm">
        <div className="flex flex-col items-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center mb-3">
            <Zap size={24} className="text-white" />
          </div>
          <h1 className="text-xl font-bold">Create your account</h1>
          <p className="text-xs text-muted-foreground mt-1">Wow Chat — by JONY</p>
        </div>

        <form onSubmit={handleRegister} className="flex flex-col gap-3">
          {[
            { key: "workspace_name", label: "Workspace Name", placeholder: "My Company" },
            { key: "username", label: "Username", placeholder: "johndoe" },
            { key: "email", label: "Email", placeholder: "john@example.com" },
            { key: "first_name", label: "First Name", placeholder: "John" },
            { key: "last_name", label: "Last Name", placeholder: "Doe" },
            { key: "password", label: "Password", placeholder: "Min 8 characters", type: "password" },
          ].map(({ key, label, placeholder, type }) => (
            <div key={key} className="flex flex-col gap-1">
              <label className="text-xs font-medium">{label}</label>
              <input
                type={type || "text"}
                className="border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder={placeholder}
                value={form[key as keyof typeof form]}
                onChange={set(key)}
                required
              />
            </div>
          ))}

          {error && (
            <p className="text-xs text-destructive bg-destructive/10 px-3 py-2 rounded-lg">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="bg-primary text-white rounded-lg py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60 mt-1"
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-center text-xs text-muted-foreground mt-4">
          Already have an account?{" "}
          <a href="/login" className="text-primary font-medium hover:underline">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
