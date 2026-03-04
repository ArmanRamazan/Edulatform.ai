import { useQuery, useMutation } from "@tanstack/react-query";
import { identity as identityApi } from "@/lib/api";

export function useReferralInfo(token: string | null) {
  return useQuery({
    queryKey: ["referral", "me"],
    queryFn: () => identityApi.getReferralInfo(token!),
    enabled: !!token,
  });
}

export function useApplyReferral(token: string | null) {
  return useMutation({
    mutationFn: (referralCode: string) =>
      identityApi.applyReferralCode(token!, { referral_code: referralCode }),
  });
}
