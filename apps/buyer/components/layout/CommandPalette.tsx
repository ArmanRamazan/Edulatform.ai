"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Network,
  Search,
  Target,
  BookOpen,
  MessageSquare,
  Bell,
  Settings,
  Zap,
  Award,
  Users,
  Rss,
} from "lucide-react";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";

interface CommandOption {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: CommandOption[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Knowledge Graph", href: "/graph", icon: Network },
  { label: "Search", href: "/search", icon: Search },
  { label: "Missions", href: "/missions", icon: Target },
  { label: "Flashcards", href: "/flashcards", icon: BookOpen },
  { label: "Messages", href: "/messages", icon: MessageSquare },
  { label: "Notifications", href: "/notifications", icon: Bell },
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "Velocity", href: "/velocity", icon: Zap },
  { label: "Badges", href: "/badges", icon: Award },
  { label: "Study Groups", href: "/groups", icon: Users },
  { label: "Activity Feed", href: "/feed", icon: Rss },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  function navigate(href: string) {
    setOpen(false);
    setInputValue("");
    router.push(href);
  }

  function searchFor(query: string) {
    setOpen(false);
    setInputValue("");
    router.push(`/search?q=${encodeURIComponent(query)}`);
  }

  const trimmedInput = inputValue.trim();

  return (
    <CommandDialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setInputValue(""); }} showCloseButton={false}>
      <CommandInput
        placeholder="Type a command or search..."
        value={inputValue}
        onValueChange={setInputValue}
      />
      <CommandList>
        <CommandEmpty>
          {trimmedInput ? (
            <button
              type="button"
              onClick={() => searchFor(trimmedInput)}
              className="flex w-full items-center gap-2 px-2 py-1.5 text-left text-sm text-[#6b6b80] hover:text-[#e2e2e8]"
            >
              <Search className="h-4 w-4" />
              Search for &ldquo;{trimmedInput}&rdquo;
            </button>
          ) : (
            "No results found."
          )}
        </CommandEmpty>
        <CommandGroup heading="Navigation">
          {NAV_ITEMS.map((item) => (
            <CommandItem
              key={item.href}
              onSelect={() => navigate(item.href)}
              className="cursor-pointer"
            >
              <item.icon className="mr-2 h-4 w-4" />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>
        {trimmedInput && (
          <CommandGroup heading="Search">
            <CommandItem
              onSelect={() => searchFor(trimmedInput)}
              className="cursor-pointer"
            >
              <Search className="mr-2 h-4 w-4" />
              Search for &ldquo;{trimmedInput}&rdquo;
            </CommandItem>
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  );
}
