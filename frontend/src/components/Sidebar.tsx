"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, Settings, LogOut, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/hooks/useStore";
import { useRouter } from "next/navigation";

const nav = [
  { href: "/dashboard", icon: MessageSquare, label: "Inbox" },
  { href: "/dashboard/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <aside className="flex flex-col w-16 bg-[#1a1a2e] text-white h-screen">
      {/* Logo */}
      <div className="flex items-center justify-center h-16 border-b border-white/10">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <Zap size={16} className="text-white" />
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1 p-2 flex-1">
        {nav.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            title={label}
            className={cn(
              "flex items-center justify-center w-12 h-12 rounded-xl transition-colors",
              pathname === href
                ? "bg-primary text-white"
                : "text-white/50 hover:bg-white/10 hover:text-white"
            )}
          >
            <Icon size={20} />
          </Link>
        ))}
      </nav>

      {/* Logout */}
      <div className="p-2 border-t border-white/10">
        <button
          onClick={handleLogout}
          title="Logout"
          className="flex items-center justify-center w-12 h-12 rounded-xl text-white/50 hover:bg-white/10 hover:text-white transition-colors"
        >
          <LogOut size={20} />
        </button>
      </div>
    </aside>
  );
}
