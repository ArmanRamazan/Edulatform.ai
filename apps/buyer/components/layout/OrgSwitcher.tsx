"use client";

import { useRouter } from "next/navigation";
import { Building2, ChevronDown, Check } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useMyOrganizations } from "@/hooks/use-organizations";
import { useActiveOrg } from "@/hooks/use-active-org";
import { type Organization } from "@/lib/api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function OrgSwitcher({ collapsed }: { collapsed: boolean }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { token } = useAuth();
  const { data: orgs } = useMyOrganizations(token);
  const { activeOrg, setActiveOrg } = useActiveOrg();

  function handleSwitch(org: Organization) {
    if (org.id === activeOrg?.id) return;
    setActiveOrg(org);
    queryClient.clear();
    router.replace("/dashboard");
  }

  if (!activeOrg) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-sidebar-accent"
          title={collapsed ? activeOrg.name : undefined}
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            {activeOrg.logo_url ? (
              <img
                src={activeOrg.logo_url}
                alt={activeOrg.name}
                className="h-5 w-5 rounded object-cover"
              />
            ) : (
              <Building2 className="h-4 w-4" />
            )}
          </div>
          {!collapsed && (
            <>
              <span className="min-w-0 flex-1 truncate text-left font-medium text-sidebar-foreground">
                {activeOrg.name}
              </span>
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-sidebar-foreground/50" />
            </>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {orgs?.map((org) => (
          <DropdownMenuItem
            key={org.id}
            onClick={() => handleSwitch(org)}
            className="flex items-center gap-2"
          >
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-primary/10 text-primary">
              {org.logo_url ? (
                <img
                  src={org.logo_url}
                  alt={org.name}
                  className="h-4 w-4 rounded object-cover"
                />
              ) : (
                <Building2 className="h-3.5 w-3.5" />
              )}
            </div>
            <span className="min-w-0 flex-1 truncate">{org.name}</span>
            {org.id === activeOrg.id && (
              <Check className="h-4 w-4 shrink-0 text-primary" />
            )}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/org/select")}>
          All organizations
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
