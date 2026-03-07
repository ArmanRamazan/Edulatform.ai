"use client";

import { use } from "react";
import Link from "next/link";
import { FollowButton } from "@/components/FollowButton";
import { useAuth } from "@/hooks/use-auth";
import { useUserProfile, useFollowCounts } from "@/hooks/use-profile";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ArrowLeft, MessageSquare, Settings, Shield, CheckCircle } from "lucide-react";

const ROLE_LABELS: Record<string, string> = {
  student: "Engineer",
  teacher: "Tech Lead",
  admin: "Admin",
};

function Initials({ name }: { name: string }) {
  const letters = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/15 text-2xl font-bold text-primary">
      {letters}
    </div>
  );
}

export default function UserProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, token } = useAuth();

  const { data: profile, error: profileError, isLoading } = useUserProfile(id);
  const { data: followCounts } = useFollowCounts(id);

  const isOwnProfile = user?.id === id;

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back
      </Link>

      {profileError ? (
        <Card className="border-destructive/30">
          <CardContent className="py-8 text-center text-sm text-destructive">
            Profile not found or unavailable
          </CardContent>
        </Card>
      ) : isLoading || !profile ? (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-start gap-5">
              <Skeleton className="h-20 w-20 rounded-full" />
              <div className="flex-1 space-y-3">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-64" />
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-5">
                {profile.avatar_url ? (
                  <img
                    src={profile.avatar_url}
                    alt={profile.name}
                    className="h-20 w-20 rounded-full object-cover ring-2 ring-border"
                  />
                ) : (
                  <Initials name={profile.name} />
                )}
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-foreground">{profile.name}</h1>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2">
                    <Badge variant="secondary" className="gap-1">
                      <Shield className="h-3 w-3" />
                      {ROLE_LABELS[profile.role] || profile.role}
                    </Badge>
                    {profile.is_verified && (
                      <Badge variant="secondary" className="gap-1 bg-success/10 text-success">
                        <CheckCircle className="h-3 w-3" />
                        Verified
                      </Badge>
                    )}
                  </div>
                  {profile.bio && (
                    <p className="mt-3 text-sm text-muted-foreground">{profile.bio}</p>
                  )}
                  <p className="mt-2 text-xs text-muted-foreground/60">
                    Member since{" "}
                    {new Date(profile.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                    })}
                  </p>
                </div>
              </div>

              <div className="mt-5 flex items-center gap-6 border-t border-border pt-4">
                <div className="text-center">
                  <span className="block text-lg font-bold text-foreground">
                    {followCounts?.followers_count ?? 0}
                  </span>
                  <span className="text-xs text-muted-foreground">followers</span>
                </div>
                <div className="text-center">
                  <span className="block text-lg font-bold text-foreground">
                    {followCounts?.following_count ?? 0}
                  </span>
                  <span className="text-xs text-muted-foreground">following</span>
                </div>
                <div className="ml-auto flex items-center gap-2">
                  {isOwnProfile ? (
                    <Button asChild variant="outline" size="sm" className="gap-1.5">
                      <Link href="/settings">
                        <Settings className="h-3.5 w-3.5" />
                        Edit profile
                      </Link>
                    </Button>
                  ) : (
                    <>
                      <FollowButton
                        token={token}
                        currentUserId={user?.id ?? null}
                        targetUserId={id}
                      />
                      {token && (
                        <Button asChild variant="outline" size="sm" className="gap-1.5">
                          <Link href={`/messages?to=${id}`}>
                            <MessageSquare className="h-3.5 w-3.5" />
                            Message
                          </Link>
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {profile.role === "teacher" && (
            <Card>
              <CardContent className="p-6">
                <h2 className="mb-2 text-lg font-bold text-foreground">Courses</h2>
                <p className="text-sm text-muted-foreground">
                  Course list coming soon
                </p>
              </CardContent>
            </Card>
          )}

          {profile.role === "student" && (
            <Card>
              <CardContent className="p-6">
                <h2 className="mb-2 text-lg font-bold text-foreground">Achievements</h2>
                <p className="text-sm text-muted-foreground">
                  Achievements coming soon
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
