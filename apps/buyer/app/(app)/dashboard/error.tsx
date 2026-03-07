"use client";

import { AlertTriangle } from "lucide-react";
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
      <Card className="border-destructive/20 bg-destructive/5">
        <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-6 w-6 text-destructive" aria-hidden="true" />
          </div>
          <div>
            <h2 className="mb-1 text-base font-semibold text-destructive">
              Ошибка загрузки
            </h2>
            <p className="text-sm text-muted-foreground">{error.message}</p>
          </div>
          <Button
            variant="outline"
            onClick={reset}
            className="mt-1"
          >
            Повторить
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
