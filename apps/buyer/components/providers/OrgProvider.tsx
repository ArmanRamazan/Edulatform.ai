"use client";

import {
  createContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useMyOrganizations } from "@/hooks/use-organizations";
import { type Organization } from "@/lib/api";

const STORAGE_KEY = "active-org-id";

interface OrgContextValue {
  activeOrg: Organization | null;
  setActiveOrg: (org: Organization) => void;
  isLoading: boolean;
}

export const OrgContext = createContext<OrgContextValue>({
  activeOrg: null,
  setActiveOrg: () => {},
  isLoading: true,
});

export function OrgProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { token, loading: authLoading } = useAuth();
  const { data: orgs, isLoading: orgsLoading } = useMyOrganizations(token);
  const [activeOrg, setActiveOrgState] = useState<Organization | null>(null);
  const [resolved, setResolved] = useState(false);

  const setActiveOrg = useCallback(
    (org: Organization) => {
      setActiveOrgState(org);
      localStorage.setItem(STORAGE_KEY, org.id);
      queryClient.clear();
    },
    [queryClient],
  );

  // Resolve active org once orgs are loaded
  useEffect(() => {
    if (authLoading || orgsLoading || !orgs) return;

    // No orgs at all — redirect to selection (will show empty state)
    if (orgs.length === 0) {
      setResolved(true);
      router.replace("/org/select");
      return;
    }

    const savedId = localStorage.getItem(STORAGE_KEY);
    const saved = savedId ? orgs.find((o) => o.id === savedId) : null;

    if (saved) {
      setActiveOrgState(saved);
      setResolved(true);
      return;
    }

    // Auto-select if only one org
    if (orgs.length === 1) {
      setActiveOrgState(orgs[0]);
      localStorage.setItem(STORAGE_KEY, orgs[0].id);
      setResolved(true);
      return;
    }

    // Multiple orgs, no valid saved — redirect to select
    setResolved(true);
    router.replace("/org/select");
  }, [authLoading, orgsLoading, orgs, router]);

  const isLoading = authLoading || orgsLoading || !resolved;

  return (
    <OrgContext.Provider value={{ activeOrg, setActiveOrg, isLoading }}>
      {children}
    </OrgContext.Provider>
  );
}
