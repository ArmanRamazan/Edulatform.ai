import { useQuery } from "@tanstack/react-query";
import { organizations } from "@/lib/api";

export function useMyOrganizations(token: string | null) {
  return useQuery({
    queryKey: ["organizations", "me"],
    queryFn: () => organizations.getMyOrgs(token!),
    enabled: !!token,
  });
}

export function useOrganization(token: string | null, orgId: string | null) {
  return useQuery({
    queryKey: ["organizations", orgId],
    queryFn: () => organizations.getOrg(token!, orgId!),
    enabled: !!token && !!orgId,
  });
}

export function useOrgMembers(token: string | null, orgId: string | null) {
  return useQuery({
    queryKey: ["organizations", orgId, "members"],
    queryFn: () => organizations.getMembers(token!, orgId!),
    enabled: !!token && !!orgId,
  });
}
