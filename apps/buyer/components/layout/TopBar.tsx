"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { Bell, Search, Flame, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useMyXp, useMyStreak } from "@/hooks/use-gamification";
import { useMyNotifications } from "@/hooks/use-notifications";
import { useWebSocket } from "@/hooks/use-websocket";
import { Skeleton } from "@/components/ui/skeleton";

// ---------------------------------------------------------------------------
// Route labels for breadcrumb display
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Breadcrumbs
// ---------------------------------------------------------------------------
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
            {i > 0 && (
              <span className="text-muted-foreground select-none">/</span>
            )}
            {isLast ? (
              <span className="text-foreground font-medium">{label}</span>
            ) : (
              <Link
                href={href}
                className="text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm"
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

// ---------------------------------------------------------------------------
// NotificationBadge
// Force-remounts (via key) on every count change to replay the pop animation.
// ---------------------------------------------------------------------------
interface NotificationBadgeProps {
  count: number;
}

function NotificationBadge({ count }: NotificationBadgeProps) {
  const [animKey, setAnimKey] = useState(0);
  const prevCountRef = useRef(count);

  useEffect(() => {
    if (count !== prevCountRef.current) {
      prevCountRef.current = count;
      setAnimKey((k) => k + 1);
    }
  }, [count]);

  if (count <= 0) return null;

  return (
    <span
      key={animKey}
      className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-primary px-1 text-[9px] font-bold text-primary-foreground animate-badge-pop pointer-events-none"
      aria-hidden="true"
    >
      {count > 99 ? "99+" : count}
    </span>
  );
}

// ---------------------------------------------------------------------------
// WsLiveDot — animated connection state indicator
// ---------------------------------------------------------------------------
interface WsLiveDotProps {
  isConnected: boolean;
  isConnecting: boolean;
}

function WsLiveDot({ isConnected, isConnecting }: WsLiveDotProps) {
  const visible = isConnected || isConnecting;

  return (
    <AnimatePresence>
      {visible && (
        <motion.span
          key={isConnected ? "connected" : "connecting"}
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className={
            isConnected
              ? "absolute bottom-0.5 right-0.5 h-1.5 w-1.5 rounded-full bg-emerald-500 ring-1 ring-card animate-ws-live-pulse"
              : "absolute bottom-0.5 right-0.5 h-1.5 w-1.5 rounded-full bg-amber-400 ring-1 ring-card animate-pulse"
          }
          aria-hidden="true"
        />
      )}
    </AnimatePresence>
  );
}

// ---------------------------------------------------------------------------
// StatChip — XP or streak pill with loading skeleton
// ---------------------------------------------------------------------------
interface StatChipProps {
  isPending: boolean;
  children: React.ReactNode;
  label: string;
  delay?: number;
}

function StatChip({ isPending, children, label, delay = 0 }: StatChipProps) {
  if (isPending) {
    return <Skeleton className="h-6 w-14 rounded-md" />;
  }

  return (
    <motion.span
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, delay, ease: "easeOut" }}
      aria-label={label}
    >
      {children}
    </motion.span>
  );
}

// ---------------------------------------------------------------------------
// TopBar
// ---------------------------------------------------------------------------
export function TopBar() {
  const { user, token } = useAuth();
  const queryClient = useQueryClient();

  const totalXp = useMyXp(token);
  const streak = useMyStreak(token);
  const notificationsQuery = useMyNotifications(token, { limit: 50 });

  // Live WebSocket connection — silently falls back if ws-gateway is down
  const { isConnected, isConnecting, notificationCount: wsCount } = useWebSocket(token);

  // When WS signals a new notification, invalidate the REST cache so the
  // unread count stays accurate without double-counting WS deltas.
  const prevWsCountRef = useRef(wsCount);
  useEffect(() => {
    if (wsCount > prevWsCountRef.current) {
      prevWsCountRef.current = wsCount;
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    }
  }, [wsCount, queryClient]);

  const unreadCount =
    notificationsQuery.data?.items?.filter((n) => !n.is_read).length ?? 0;

  function handleCommandK() {
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true })
    );
  }

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-card px-4">
      {/* Left: breadcrumbs */}
      <Breadcrumbs />

      {/* Center: Cmd+K trigger */}
      <button
        onClick={handleCommandK}
        className="hidden items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-muted-foreground transition-all hover:bg-card hover:text-foreground hover:border-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:flex"
        aria-label="Open command palette"
      >
        <Search className="h-3.5 w-3.5" />
        <span>Search...</span>
        <kbd className="ml-2 rounded border border-border bg-card px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
          {"\u2318K"}
        </kbd>
      </button>

      {/* Right: stats + notifications */}
      <div className="flex items-center gap-3">
        {user && (
          <>
            {/* XP chip */}
            <StatChip
              isPending={totalXp.isPending}
              label={`${totalXp.data ?? 0} XP earned`}
              delay={0}
            >
              <span className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-semibold text-primary">
                <Zap className="h-3 w-3" aria-hidden="true" />
                {totalXp.data ?? 0}
              </span>
            </StatChip>

            {/* Streak chip */}
            <StatChip
              isPending={streak.isPending}
              label={`${streak.data?.current_streak ?? 0} day streak`}
              delay={0.05}
            >
              <span className="flex items-center gap-1 rounded-md bg-warning/10 px-2 py-1 text-xs font-semibold text-warning">
                <Flame className="h-3.5 w-3.5" aria-hidden="true" />
                {streak.data?.current_streak ?? 0}
              </span>
            </StatChip>
          </>
        )}

        {/*
          Bell button — shows:
          • Live unread badge (REST-backed, refreshed on WS event)
          • WS live-dot: emerald (connected) or amber (connecting), pulsing
          • aria-live region announces count changes to screen readers
        */}
        <Link
          href="/notifications"
          className="relative rounded-md p-1.5 text-muted-foreground transition-all hover:bg-muted/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background"
          aria-label={
            unreadCount > 0
              ? `Notifications — ${unreadCount} unread`
              : "Notifications"
          }
        >
          {/* Bell icon */}
          <Bell className="h-4 w-4" aria-hidden="true" />

          {/* WS live indicator — emerald (connected) / amber (connecting) */}
          <WsLiveDot isConnected={isConnected} isConnecting={isConnecting} />

          {/* Unread count badge with pop animation */}
          <NotificationBadge count={unreadCount} />
        </Link>

        {/* Screen-reader live region — announces unread count changes */}
        <span className="sr-only" aria-live="polite" aria-atomic="true">
          {unreadCount > 0
            ? `${unreadCount} unread notification${unreadCount !== 1 ? "s" : ""}`
            : ""}
        </span>
      </div>
    </header>
  );
}
