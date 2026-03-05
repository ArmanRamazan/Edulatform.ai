"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { Bell, Search, Flame } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMyXp, useMyStreak } from "@/hooks/use-gamification";
import { useMyNotifications } from "@/hooks/use-notifications";

const ROUTE_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  graph: "Graph",
  search: "Search",
  missions: "Missions",
  flashcards: "Flashcards",
  messages: "Messages",
  notifications: "Notifications",
  settings: "Settings",
  enrollments: "My Courses",
  "my-courses": "My Courses",
  velocity: "Velocity",
  badges: "Badges",
  referral: "Referral",
  feed: "Feed",
  groups: "Study Groups",
  wishlist: "Wishlist",
  bundles: "Bundles",
  courses: "Courses",
  admin: "Admin",
  users: "Users",
};

function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm">
      {segments.map((segment, i) => {
        const href = "/" + segments.slice(0, i + 1).join("/");
        const label = ROUTE_LABELS[segment] ?? segment;
        const isLast = i === segments.length - 1;

        return (
          <span key={href} className="flex items-center gap-1">
            {i > 0 && <span className="text-muted-foreground">/</span>}
            {isLast ? (
              <span className="text-foreground font-medium">{label}</span>
            ) : (
              <Link
                href={href}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export function TopBar() {
  const { user, token } = useAuth();
  const totalXp = useMyXp(token);
  const streak = useMyStreak(token);
  const notificationsQuery = useMyNotifications(token, { limit: 50 });

  const unreadCount =
    notificationsQuery.data?.items?.filter((n) => !n.is_read).length ?? 0;

  function handleCommandK() {
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
  }

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-card px-4">
      {/* Left: breadcrumbs */}
      <Breadcrumbs />

      {/* Center: Cmd+K trigger */}
      <button
        onClick={handleCommandK}
        className="hidden items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-card hover:text-foreground sm:flex"
      >
        <Search className="h-3.5 w-3.5" />
        <span>Search...</span>
        <kbd className="ml-2 rounded border border-border bg-card px-1.5 py-0.5 text-[10px]">
          {"\u2318K"}
        </kbd>
      </button>

      {/* Right: stats + notifications */}
      <div className="flex items-center gap-3">
        {user && (
          <>
            <span className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-semibold text-primary">
              XP {totalXp.data ?? 0}
            </span>

            <span className="flex items-center gap-1 rounded-md bg-warning/10 px-2 py-1 text-xs font-semibold text-warning">
              <Flame className="h-3.5 w-3.5" />
              {streak.data?.current_streak ?? 0}
            </span>
          </>
        )}

        <Link
          href="/notifications"
          className="relative rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-card hover:text-foreground"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-primary px-1 text-[9px] font-bold text-primary-foreground">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </Link>
      </div>
    </header>
  );
}
