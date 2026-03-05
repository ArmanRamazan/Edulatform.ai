"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-7xl">
      <Card className="border-destructive/30 bg-destructive/5">
        <CardContent className="flex flex-col items-center py-12 text-center">
          <h2 className="mb-2 text-lg font-bold text-destructive">
            Something went wrong
          </h2>
          <p className="mb-4 text-sm text-muted-foreground">{error.message}</p>
          <Button variant="outline" onClick={reset}>
            Try again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
