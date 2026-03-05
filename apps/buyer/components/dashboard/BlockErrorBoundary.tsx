"use client";

import { Component, type ReactNode } from "react";
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
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <p className="mb-1 text-sm font-medium text-destructive">
              {this.props.fallbackTitle ?? "Failed to load"}
            </p>
            <p className="mb-3 text-xs text-muted-foreground">
              {this.state.error.message}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => this.setState({ error: null })}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
