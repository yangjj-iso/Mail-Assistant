"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "仪表盘" },
  { href: "/inbox", label: "收件箱" },
  { href: "/kanban", label: "求职看板" },
  { href: "/schedule", label: "面试日程" },
  { href: "/settings", label: "设置" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r bg-muted/30 flex flex-col p-4 gap-2 h-screen sticky top-0">
      <div className="font-semibold text-lg px-3 py-2 mb-4">
        Mail Assistant
      </div>
      <nav className="flex flex-col gap-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              pathname === item.href
                ? "bg-primary text-primary-foreground"
                : "hover:bg-muted"
            )}
          >
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
