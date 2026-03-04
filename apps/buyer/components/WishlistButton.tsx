"use client";

import { useIsInWishlist, useToggleWishlist } from "@/hooks/use-wishlist";

interface WishlistButtonProps {
  token: string | null;
  courseId: string;
}

export function WishlistButton({ token, courseId }: WishlistButtonProps) {
  const { data } = useIsInWishlist(token, courseId);
  const toggle = useToggleWishlist(token);

  if (!token) return null;

  const inWishlist = data?.in_wishlist ?? false;

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    toggle.mutate({ courseId, inWishlist });
  }

  return (
    <button
      onClick={handleClick}
      disabled={toggle.isPending}
      className={`rounded-full bg-white/80 p-1.5 shadow transition hover:bg-white ${toggle.isPending ? "opacity-50" : ""}`}
      aria-label={inWishlist ? "Remove from wishlist" : "Add to wishlist"}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        className="h-5 w-5"
        fill={inWishlist ? "#ef4444" : "none"}
        stroke={inWishlist ? "#ef4444" : "currentColor"}
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
        />
      </svg>
    </button>
  );
}
