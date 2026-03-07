"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

export function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const complete = localStorage.getItem("onboarding_complete") === "true";

    if (!complete && pathname !== "/onboarding") {
      router.replace("/onboarding");
      return;
    }

    if (complete && pathname === "/onboarding") {
      router.replace("/dashboard");
      return;
    }

    setChecked(true);
  }, [pathname, router]);

  if (!checked) {
    return (
      <div
        className="flex h-screen items-center justify-center"
        style={{ background: "#07070b" }}
      />
    );
  }

  return <>{children}</>;
}
