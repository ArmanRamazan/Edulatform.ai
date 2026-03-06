import { useQuery } from "@tanstack/react-query";
import { bundles } from "@/lib/api";

export function useBundleList(params?: {
  limit?: number;
  offset?: number;
  teacher_id?: string;
}) {
  return useQuery({
    queryKey: ["bundles", params],
    queryFn: () => bundles.list(params),
  });
}

export function useBundle(id: string) {
  return useQuery({
    queryKey: ["bundles", id],
    queryFn: () => bundles.get(id),
  });
}
