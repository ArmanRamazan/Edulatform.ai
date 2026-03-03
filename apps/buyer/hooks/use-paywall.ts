import { useState, useCallback } from "react";
import { useAICredits } from "@/hooks/use-ai";

export function usePaywall(token: string | null) {
  const { data: creditStatus } = useAICredits(token);
  const [paywallOpen, setPaywallOpen] = useState(false);

  const showPaywall =
    creditStatus?.remaining === 0 && creditStatus?.tier !== "pro";

  const openPaywall = useCallback(() => setPaywallOpen(true), []);
  const closePaywall = useCallback(() => setPaywallOpen(false), []);

  return { showPaywall, paywallOpen, openPaywall, closePaywall, creditStatus };
}
