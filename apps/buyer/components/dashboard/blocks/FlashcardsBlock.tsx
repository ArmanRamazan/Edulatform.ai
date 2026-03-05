"use client";

import Link from "next/link";
import { BookOpen, Check } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useDueCount } from "@/hooks/use-flashcards";

const BLOCK_ANIMATION = {
  initial: { opacity: 0, scale: 0.97 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.3 },
};

export function FlashcardsBlock() {
  const { token } = useAuth();
  const { data: dueCount, isLoading, error } = useDueCount(token);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-20" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-4 w-32" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/30">
        <CardContent className="py-5 text-sm text-destructive">
          Failed to load flashcards
        </CardContent>
      </Card>
    );
  }

  const count = dueCount ?? 0;

  return (
    <motion.div {...BLOCK_ANIMATION}>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Flashcards
            </CardTitle>
            <BookOpen className="size-4 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-3xl font-bold text-card-foreground">
            {count}
          </p>
          {count === 0 ? (
            <div className="mt-2 flex items-center gap-1.5 text-sm text-success">
              <Check className="size-4" />
              All caught up!
            </div>
          ) : (
            <>
              <p className="mb-3 text-sm text-muted-foreground">
                {count === 1 ? "card" : "cards"} due for review
              </p>
              <Button variant="outline" size="sm" asChild>
                <Link href="/flashcards">Review cards</Link>
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
