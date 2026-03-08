"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Network,
  Search,
  Target,
  BookOpen,
  MessageSquare,
  Bell,
  Settings,
  PanelLeftClose,
  PanelLeft,
  Menu,
  Layers,
  Building2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { useMyNotifications } from "@/hooks/use-notifications";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { OrgSwitcher } from "@/components/layout/OrgSwitcher";

const STORAGE_KEY = "sidebar-collapsed";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
  shortcut?: string;
}

function SidebarNav({
  items,
  pathname,
  collapsed,
}: {
  items: NavItem[];
  pathname: string;
  collapsed: boolean;
}) {
  return (
    <nav className="flex flex-col gap-1 px-2">
      {items.map((item) => {
        const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
        const linkCls = cn(
          "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150",
          isActive
            ? "border-l-2 border-sidebar-primary bg-sidebar-accent text-sidebar-primary-foreground"
            : "border-l-2 border-transparent text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
          collapsed && "justify-center px-2",
        );

        if (collapsed) {
          return (
            <Tooltip key={item.href}>
              <TooltipTrigger asChild>
                <Link href={item.href} className={linkCls}>
                  <item.icon className="h-5 w-5 shrink-0" />
                  {item.badge != null && item.badge > 0 && (
                    <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-primary px-1 text-[9px] font-semibold text-primary-foreground">
                      {item.badge > 99 ? "99+" : item.badge}
                    </span>
                  )}
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right" className="flex items-center gap-1.5 text-xs">
                {item.label}
                {item.badge != null && item.badge > 0 && (
                  <span className="rounded-full bg-primary px-1.5 py-0.5 text-[9px] font-semibold text-primary-foreground">
                    {item.badge > 99 ? "99+" : item.badge}
                  </span>
                )}
              </TooltipContent>
            </Tooltip>
          );
        }

        return (
          <Link key={item.href} href={item.href} className={linkCls}>
            <item.icon className="h-5 w-5 shrink-0" />
            <span className="truncate">{item.label}</span>
            {item.shortcut && (
              <kbd className="ml-auto rounded border border-sidebar-border bg-sidebar px-1.5 py-0.5 text-[10px] text-sidebar-foreground/50">
                {item.shortcut}
              </kbd>
            )}
            {item.badge != null && item.badge > 0 && (
              <span className="ml-auto flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
                {item.badge > 99 ? "99+" : item.badge}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarContent({
  collapsed,
  onToggle,
  navItems,
  bottomItems,
  user,
}: {
  collapsed: boolean;
  onToggle: () => void;
  navItems: NavItem[];
  bottomItems: NavItem[];
  user: { name: string; role: string } | null;
}) {
  const pathname = usePathname();
  return (
    <div className="flex h-full flex-col bg-sidebar">
      {/* Header: logo + toggle */}
      <div className="flex h-14 items-center justify-between border-b border-sidebar-border px-3">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/20">
              <Layers className="h-3.5 w-3.5 text-primary" />
            </div>
            <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
              KnowledgeOS
            </span>
          </div>
        )}
        <button
          onClick={onToggle}
          className="rounded-md p-1.5 text-sidebar-foreground/50 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeft className="h-5 w-5" />
          ) : (
            <PanelLeftClose className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* Org switcher */}
      <div className="px-2 py-2">
        <OrgSwitcher collapsed={collapsed} />
      </div>

      {/* Main nav */}
      <div className="mt-2 flex-1 overflow-y-auto">
        <SidebarNav items={navItems} pathname={pathname} collapsed={collapsed} />
      </div>

      {/* Separator */}
      <div className="mx-3 border-t border-sidebar-border" />

      {/* Bottom nav */}
      <div className="py-2">
        <SidebarNav items={bottomItems} pathname={pathname} collapsed={collapsed} />
      </div>

      {/* User */}
      {user && (
        <div className="border-t border-sidebar-border px-3 py-3">
          <div className={cn("flex items-center gap-3", collapsed && "justify-center")}>
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
              {user.name.charAt(0).toUpperCase()}
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-sidebar-foreground">
                  {user.name}
                </p>
                <p className="text-xs text-sidebar-foreground/50 capitalize">
                  {user.role}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const { user, token } = useAuth();
  const notificationsQuery = useMyNotifications(token, { limit: 50 });

  const unreadCount =
    notificationsQuery.data?.items?.filter((n) => !n.is_read).length ?? 0;

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) {
      setCollapsed(saved === "true");
    }
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  function handleToggle() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  }

  const navItems: NavItem[] = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/graph", label: "Graph", icon: Network },
    { href: "/search", label: "Search", icon: Search, shortcut: "\u2318K" },
    { href: "/missions", label: "Missions", icon: Target },
    { href: "/flashcards", label: "Flashcards", icon: BookOpen },
    { href: "/messages", label: "Messages", icon: MessageSquare },
    { href: "/notifications", label: "Notifications", icon: Bell, badge: unreadCount },
  ];

  const bottomItems: NavItem[] = [
    { href: "/org/admin", label: "Org Admin", icon: Building2 },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden h-screen shrink-0 border-r border-sidebar-border transition-[width] duration-200 ease-in-out md:block",
          collapsed ? "w-16" : "w-60",
        )}
      >
        <SidebarContent
          collapsed={collapsed}
          onToggle={handleToggle}
          navItems={navItems}
          bottomItems={bottomItems}
          user={user}
        />
      </aside>

      {/* Mobile trigger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed bottom-4 left-4 z-40 flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg md:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-60 p-0" showCloseButton={false}>
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent
            collapsed={false}
            onToggle={() => setMobileOpen(false)}
            navItems={navItems}
            bottomItems={bottomItems}
            user={user}
          />
        </SheetContent>
      </Sheet>
    </>
  );
}
