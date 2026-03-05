"use client";

import { useRouter } from "next/navigation";
import { Building2, Users } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMyOrganizations, useOrgMembers } from "@/hooks/use-organizations";
import { useActiveOrg } from "@/hooks/use-active-org";
import { type Organization } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

function OrgCard({
  org,
  onSelect,
}: {
  org: Organization;
  onSelect: (org: Organization) => void;
}) {
  const { token } = useAuth();
  const membersQuery = useOrgMembers(token, org.id);
  const memberCount = membersQuery.data?.length ?? 0;

  return (
    <button
      onClick={() => onSelect(org)}
      className="group relative flex flex-col items-center gap-4 rounded-xl border border-border bg-card p-6 text-left transition-all duration-200 hover:border-primary/50 hover:shadow-[0_0_24px_rgba(124,92,252,0.15)]"
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary/20">
        {org.logo_url ? (
          <img
            src={org.logo_url}
            alt={org.name}
            className="h-10 w-10 rounded-lg object-cover"
          />
        ) : (
          <Building2 className="h-8 w-8" />
        )}
      </div>
      <div className="flex flex-col items-center gap-1">
        <h3 className="text-lg font-semibold text-foreground">{org.name}</h3>
        <span className="text-sm text-muted-foreground">{org.slug}</span>
      </div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Users className="h-3.5 w-3.5" />
        <span>
          {membersQuery.isLoading
            ? "..."
            : `${memberCount} member${memberCount !== 1 ? "s" : ""}`}
        </span>
      </div>
    </button>
  );
}

export default function OrgSelectPage() {
  const router = useRouter();
  const { token } = useAuth();
  const { data: orgs, isLoading } = useMyOrganizations(token);
  const { setActiveOrg } = useActiveOrg();

  function handleSelect(org: Organization) {
    setActiveOrg(org);
    router.replace("/dashboard");
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 w-64 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!orgs || orgs.length === 0) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <Building2 className="h-12 w-12 text-muted-foreground" />
        <h2 className="text-xl font-semibold text-foreground">
          No Organizations
        </h2>
        <p className="text-sm text-muted-foreground">
          You are not a member of any organization yet.
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-8">
      <div className="flex flex-col items-center gap-2">
        <h1 className="text-2xl font-bold text-foreground">
          Select Organization
        </h1>
        <p className="text-sm text-muted-foreground">
          Choose a workspace to continue
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {orgs.map((org) => (
          <OrgCard key={org.id} org={org} onSelect={handleSelect} />
        ))}
      </div>
    </div>
  );
}
