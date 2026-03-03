import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { subscriptions } from "@/lib/api";

export function useSubscriptionPlans() {
  return useQuery({
    queryKey: ["subscription", "plans"],
    queryFn: () => subscriptions.plans(),
  });
}

export function useMySubscription(token: string | null) {
  return useQuery({
    queryKey: ["subscription", "me"],
    queryFn: () => subscriptions.me(token!),
    enabled: !!token,
  });
}

export function useCreateSubscription(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { plan_id: string; payment_method_id: string }) =>
      subscriptions.create(token!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription", "me"] });
      queryClient.invalidateQueries({ queryKey: ["ai-credits"] });
    },
  });
}

export function useCancelSubscription(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => subscriptions.cancel(token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription", "me"] });
      queryClient.invalidateQueries({ queryKey: ["ai-credits"] });
    },
  });
}
