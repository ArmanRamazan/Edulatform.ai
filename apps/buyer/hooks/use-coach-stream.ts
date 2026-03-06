"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { coach as coachApi } from "@/lib/api";
import type { CoachPhase } from "@/lib/api";

interface SSETokenEvent {
  token: string;
  done: false;
}

interface SSEDoneEvent {
  token: string;
  done: true;
  full_text: string;
  phase?: CoachPhase;
}

type SSEEvent = SSETokenEvent | SSEDoneEvent;

export interface UseCoachStreamOptions {
  sessionId: string | null;
  token: string;
  onComplete: (text: string, phase?: CoachPhase) => void;
  onFallbackError: (err: Error) => void;
}

export interface CoachStreamState {
  /** Waiting for first SSE token (or fallback POST to resolve) */
  isPending: boolean;
  /** Tokens are actively arriving */
  isStreaming: boolean;
  /** Accumulated text so far */
  currentText: string;
  /** Stream finished — message committed via onComplete */
  isComplete: boolean;
}

export function useCoachStream({
  sessionId,
  token,
  onComplete,
  onFallbackError,
}: UseCoachStreamOptions): CoachStreamState & {
  startStream: (userMessage: string) => void;
  reset: () => void;
} {
  const [state, setState] = useState<CoachStreamState>({
    isPending: false,
    isStreaming: false,
    currentText: "",
    isComplete: false,
  });

  const esRef = useRef<EventSource | null>(null);
  const accumulatedRef = useRef("");

  // Keep callbacks in refs so they're always fresh without being hook deps
  const onCompleteRef = useRef(onComplete);
  const onFallbackErrorRef = useRef(onFallbackError);
  onCompleteRef.current = onComplete;
  onFallbackErrorRef.current = onFallbackError;

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  const reset = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    accumulatedRef.current = "";
    setState({ isPending: false, isStreaming: false, currentText: "", isComplete: false });
  }, []);

  const startStream = useCallback(
    (userMessage: string) => {
      if (!sessionId) return;

      // Reset accumulated state before new request
      accumulatedRef.current = "";
      esRef.current?.close();
      setState({ isPending: true, isStreaming: false, currentText: "", isComplete: false });

      const params = new URLSearchParams({ message: userMessage, token });
      const url = `/api/ai/coach/stream/${sessionId}?${params.toString()}`;

      const es = new EventSource(url);
      esRef.current = es;

      es.onmessage = (event: MessageEvent<string>) => {
        try {
          const data = JSON.parse(event.data) as SSEEvent;

          if (data.done) {
            es.close();
            esRef.current = null;
            const finalText = data.full_text ?? accumulatedRef.current;
            setState({ isPending: false, isStreaming: false, currentText: finalText, isComplete: true });
            onCompleteRef.current(finalText, data.phase);
          } else {
            accumulatedRef.current += data.token;
            setState({
              isPending: false,
              isStreaming: true,
              currentText: accumulatedRef.current,
              isComplete: false,
            });
          }
        } catch {
          // Ignore malformed SSE JSON
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;

        // Fallback: regular POST — keeps TypingIndicator visible during the request
        coachApi
          .sendMessage(token, sessionId, userMessage)
          .then((data) => {
            setState({
              isPending: false,
              isStreaming: false,
              currentText: data.reply,
              isComplete: true,
            });
            onCompleteRef.current(data.reply, data.phase);
          })
          .catch((err: unknown) => {
            setState({ isPending: false, isStreaming: false, currentText: "", isComplete: false });
            onFallbackErrorRef.current(err instanceof Error ? err : new Error(String(err)));
          });
      };
    },
    [sessionId, token],
  );

  return { ...state, startStream, reset };
}
