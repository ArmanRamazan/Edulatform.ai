"use client";

import { Component, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface BlockErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
}

interface BlockErrorBoundaryState {
  error: Error | null;
}

export class BlockErrorBoundary extends Component<
  BlockErrorBoundaryProps,
  BlockErrorBoundaryState
> {
  constructor(props: BlockErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): BlockErrorBoundaryState {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <Card className="border-destructive/30 bg-destructive/5" role="alert">
          <CardContent className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <AlertCircle
              className="h-5 w-5 text-destructive"
              aria-hidden="true"
              strokeWidth={1.5}
            />
            <p className="text-sm font-medium text-destructive">
              {this.props.fallbackTitle ?? "Something went wrong"}
            </p>
            <p className="text-xs text-muted-foreground">
              This section couldn&apos;t load. Try again.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-1"
              onClick={() => this.setState({ error: null })}
            >
              Try again
            </Button>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
