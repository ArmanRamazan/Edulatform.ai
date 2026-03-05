"use client";

import { useContext } from "react";
import { OrgContext } from "@/components/providers/OrgProvider";

export function useActiveOrg() {
  return useContext(OrgContext);
}
