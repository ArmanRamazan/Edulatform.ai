"use client";

import { useFollowUser, useUnfollowUser, useMyFollowing } from "@/hooks/use-profile";

interface FollowButtonProps {
  token: string | null;
  currentUserId: string | null;
  targetUserId: string;
}

export function FollowButton({ token, currentUserId, targetUserId }: FollowButtonProps) {
  const { data: followingData } = useMyFollowing(token);
  const follow = useFollowUser(token, targetUserId);
  const unfollow = useUnfollowUser(token, targetUserId);

  if (!token || !currentUserId || currentUserId === targetUserId) {
    return null;
  }

  const isFollowing = followingData?.items.some((f) => f.following_id === targetUserId) ?? false;
  const isPending = follow.isPending || unfollow.isPending;

  function handleClick() {
    if (isFollowing) {
      unfollow.mutate();
    } else {
      follow.mutate();
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={isPending}
      className={`rounded px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 ${
        isFollowing
          ? "bg-gray-200 text-gray-700 hover:bg-gray-300"
          : "bg-blue-600 text-white hover:bg-blue-700"
      }`}
    >
      {isPending
        ? "..."
        : isFollowing
          ? "Отписаться"
          : "Подписаться"}
    </button>
  );
}
