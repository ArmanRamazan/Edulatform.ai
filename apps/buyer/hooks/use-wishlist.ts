import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { wishlist } from "@/lib/api";

export function useMyWishlist(token: string | null) {
  return useQuery({
    queryKey: ["wishlist", "me"],
    queryFn: () => wishlist.me(token!),
    enabled: !!token,
  });
}

export function useIsInWishlist(token: string | null, courseId: string) {
  return useQuery({
    queryKey: ["wishlist", "check", courseId],
    queryFn: () => wishlist.check(token!, courseId),
    enabled: !!token && !!courseId,
  });
}

export function useToggleWishlist(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ courseId, inWishlist }: { courseId: string; inWishlist: boolean }) => {
      if (!token) throw new Error("Not authenticated");
      if (inWishlist) {
        await wishlist.remove(token, courseId);
      } else {
        await wishlist.add(token, courseId);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
    },
  });
}
