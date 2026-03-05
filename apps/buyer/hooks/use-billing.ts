import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { orgBilling } from "@/lib/api";

export function useOrgSubscription(
  token: string | null,
  orgId: string | null,
) {
  return useQuery({
    queryKey: ["org-billing", orgId],
    queryFn: () => orgBilling.getSubscription(token!, orgId!),
    enabled: !!token && !!orgId,
  });
}

export function useCreateOrgSubscription(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      plan_tier: string;
      payment_method_id: string;
      org_email: string;
      org_name: string;
    }) => orgBilling.createSubscription(token!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-billing"] });
    },
  });
}

export function useCancelOrgSubscription(
  token: string | null,
  orgId: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => orgBilling.cancelSubscription(token!, orgId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-billing"] });
    },
  });
}
