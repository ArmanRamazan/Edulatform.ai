"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { SendHorizontal, AlertCircle, Lightbulb, LogOut } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { getErrorMessage } from "@/lib/errors";
import {
  useStartCoachSession,
  useEndCoachSession,
  useCompleteMissionWithCoach,
  type CoachMessage,
  type CoachPhase,
} from "@/hooks/use-coach";
import { useCoachStream } from "@/hooks/use-coach-stream";
import { PhaseIndicator } from "./PhaseIndicator";
import { MissionComplete } from "./MissionComplete";
import { TypingIndicator } from "./TypingIndicator";
import { StreamingMessage } from "./StreamingMessage";
import type { Mission, CoachEndResponse, MissionBlueprint } from "@/lib/api";

interface MissionSessionProps {
  mission: Mission;
  token: string;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-[#ffffff08]">
      {/* Language label strip */}
      <div className="flex items-center border-b border-[#ffffff08] bg-[#07070b] px-3 py-1.5">
        <span className="font-mono text-[10px] uppercase tracking-widest text-[#6b6b80]">
          {language || "code"}
        </span>
      </div>
      <pre className="overflow-x-auto bg-[#07070b] p-4 font-mono text-xs leading-relaxed text-[#e2e2e8]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function renderMessageContent(content: string) {
  const parts = content.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const lines = part.slice(3, -3).split("\n");
      const lang = lines[0]?.trim();
      const code = lang ? lines.slice(1).join("\n") : lines.join("\n");
      return <CodeBlock key={i} code={code} language={lang} />;
    }
    const trimmed = part.trim();
    return trimmed ? (
      <p key={i} className="whitespace-pre-wrap text-[#e2e2e8]">
        {part}
      </p>
    ) : null;
  });
}

function ContentArea({
  phase,
  blueprint,
}: {
  phase: CoachPhase;
  blueprint: MissionBlueprint | null;
}) {
  if (!blueprint) {
    return (
      <div className="space-y-3 p-6">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6">
      {phase === "recap" && (
        <>
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Recap — {blueprint.concept_name}
          </h3>
          {blueprint.recap_questions.length > 0 ? (
            <div className="space-y-3">
              {(blueprint.recap_questions as string[]).map((q, i) => (
                <Card key={i} className="border-[#ffffff08] bg-[#14141f]">
                  <CardContent className="p-4">
                    <p className="text-sm text-[#e2e2e8]">{q}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Let&apos;s start by reviewing what you already know about{" "}
              <span className="font-medium text-primary">{blueprint.concept_name}</span>.
            </p>
          )}
        </>
      )}

      {phase === "reading" && (
        <>
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Reading Material
          </h3>
          <div className="prose-invert max-w-none">
            <div className="rounded-lg border border-[#ffffff08] bg-[#0a0a0f] p-4 text-sm leading-relaxed text-[#e2e2e8]">
              {blueprint.reading_content || "No reading material available for this mission."}
            </div>
          </div>
        </>
      )}

      {phase === "questions" && (
        <>
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Check Questions
          </h3>
          <div className="space-y-3">
            {(blueprint.check_questions as Array<{ question: string; options?: string[] }>).map(
              (q, i) => (
                <Card key={i} className="border-[#ffffff08] bg-[#14141f]">
                  <CardContent className="p-4">
                    <p className="mb-2 text-sm font-medium text-[#e2e2e8]">{q.question}</p>
                    {q.options && (
                      <div className="space-y-1.5">
                        {q.options.map((opt, j) => (
                          <div
                            key={j}
                            className="cursor-pointer rounded-lg bg-[#1a1a2e] px-3 py-2 text-xs text-[#a0a0b0] transition-colors hover:bg-primary/10 hover:text-[#e2e2e8]"
                          >
                            {opt}
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ),
            )}
          </div>
        </>
      )}

      {phase === "code_case" && (
        <>
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Code Challenge
          </h3>
          {blueprint.code_case ? (
            <div className="space-y-3">
              <CodeBlock
                code={
                  typeof blueprint.code_case === "string"
                    ? blueprint.code_case
                    : JSON.stringify(blueprint.code_case, null, 2)
                }
              />
              <p className="text-xs text-muted-foreground">
                Discuss your solution with the coach in the chat.
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No code case for this mission. Chat with the coach to continue.
            </p>
          )}
        </>
      )}

      {phase === "wrap_up" && (
        <div className="flex flex-col items-center gap-4 py-8 text-center">
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Wrapping Up
          </div>
          <p className="text-sm text-muted-foreground">
            The coach will summarize your session. End the session when ready.
          </p>
        </div>
      )}
    </div>
  );
}

export function MissionSession({ mission, token }: MissionSessionProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [phase, setPhase] = useState<CoachPhase>("recap");
  const [completedPhases, setCompletedPhases] = useState<Set<CoachPhase>>(new Set());
  const [messages, setMessages] = useState<CoachMessage[]>([]);
  const [input, setInput] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [endResults, setEndResults] = useState<CoachEndResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const startSession = useStartCoachSession(token);
  const endSession = useEndCoachSession(token);
  const completeMission = useCompleteMissionWithCoach(token);

  // Auto-scroll on new committed messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Session timer
  useEffect(() => {
    if (!sessionId || endResults) return;
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, [sessionId, endResults]);

  // Start session on mount
  useEffect(() => {
    if (sessionId) return;
    startSession.mutate(mission.id, {
      onSuccess: (data) => {
        setSessionId(data.session_id);
        setPhase(data.phase);
        setMessages([{ role: "coach", content: data.greeting, phase: data.phase }]);
      },
      onError: (err) => setError(getErrorMessage(err, "Failed to start session")),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updatePhase = useCallback(
    (newPhase: CoachPhase) => {
      if (newPhase !== phase) {
        setCompletedPhases((prev) => new Set([...prev, phase]));
        setPhase(newPhase);
      }
    },
    [phase],
  );

  // Streaming hook — SSE with automatic POST fallback on connection error
  const coachStream = useCoachStream({
    sessionId,
    token,
    onComplete: useCallback(
      (text: string, newPhase?: CoachPhase) => {
        setMessages((prev) => [...prev, { role: "coach", content: text, phase: newPhase }]);
        if (newPhase) updatePhase(newPhase);
      },
      [updatePhase],
    ),
    onFallbackError: useCallback((err: Error) => {
      setMessages((prev) => [
        ...prev,
        { role: "coach", content: `Error: ${getErrorMessage(err)}` },
      ]);
    }, []),
  });

  // True when input should be blocked
  const isBusy =
    startSession.isPending || coachStream.isPending || coachStream.isStreaming;

  // Show TypingIndicator row (before first token or during initial session start)
  const showTypingIndicator =
    startSession.isPending || (coachStream.isPending && !coachStream.isStreaming);

  // Show StreamingMessage row (tokens are actively flowing)
  const showStreamingMessage = coachStream.isStreaming && coachStream.currentText.length > 0;

  // Auto-focus the input when the session becomes ready
  useEffect(() => {
    if (sessionId && !isBusy) {
      inputRef.current?.focus();
    }
  }, [sessionId, isBusy]);

  function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || !sessionId || isBusy) return;

    setInput("");
    // Reset textarea height after clearing
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    coachStream.startStream(msg);
  }

  function handleEnd() {
    if (!sessionId || endSession.isPending) return;
    endSession.mutate(sessionId, {
      onSuccess: (data) => {
        setEndResults(data);
        completeMission.mutate({ missionId: mission.id, sessionId });
      },
      onError: (err) => setError(getErrorMessage(err, "Failed to end session")),
    });
  }

  /** Auto-grow textarea up to ~5 lines; Escape clears the draft. */
  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === "Escape") {
      setInput("");
      if (inputRef.current) {
        inputRef.current.style.height = "auto";
      }
    }
  }

  if (endResults) {
    return <MissionComplete results={endResults} />;
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <Card className="border-destructive/20 bg-[#14141f]">
          <CardContent className="flex flex-col items-center gap-3 p-6 text-center">
            <div className="flex size-10 items-center justify-center rounded-full bg-destructive/10">
              <AlertCircle className="size-5 text-destructive" />
            </div>
            <p className="text-sm text-[#e2e2e8]">{error}</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-1 border-[#ffffff12] text-[#a0a0b0] hover:border-[#ffffff20] hover:text-[#e2e2e8]"
              onClick={() => window.location.reload()}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#ffffff08] px-6 py-3">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-sm font-semibold text-[#e2e2e8]">
              {mission.blueprint?.concept_name ?? "Mission"}
            </h2>
            <p className="text-xs text-[#6b6b80]">{mission.mission_type}</p>
          </div>
          <PhaseIndicator currentPhase={phase} completedPhases={completedPhases} />
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="font-mono text-xs tabular-nums">
            {formatElapsed(elapsed)}
          </Badge>
          <Button
            size="sm"
            variant="outline"
            aria-label="End the coaching session"
            className="gap-1.5 border-[#ffffff12] text-[#a0a0b0] transition-colors hover:border-destructive/40 hover:bg-destructive/10 hover:text-destructive"
            onClick={handleEnd}
            disabled={endSession.isPending || !sessionId}
          >
            <LogOut className="size-3.5" aria-hidden="true" />
            {endSession.isPending ? "Ending…" : "End Session"}
          </Button>
        </div>
      </div>

      {/* Two-panel layout */}
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Left panel — Content */}
        <div className="flex-[3] overflow-y-auto border-b border-[#ffffff08] md:border-b-0 md:border-r">
          <ContentArea phase={phase} blueprint={mission.blueprint} />
        </div>

        {/* Right panel — Coach Chat */}
        <div className="flex min-h-0 flex-[2] flex-col">
          {/* Messages */}
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-3">
              {/* Initial loading skeleton — shown before the session greeting arrives */}
              {messages.length === 0 && startSession.isPending && (
                <div className="space-y-3" aria-hidden="true">
                  <div className="flex gap-2">
                    <Skeleton className="size-7 shrink-0 rounded-full" />
                    <div className="space-y-1.5">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-4 w-64" />
                      <Skeleton className="h-4 w-40" />
                    </div>
                  </div>
                </div>
              )}

              {/* Committed messages */}
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex gap-2",
                    msg.role === "user" ? "justify-end" : "justify-start",
                  )}
                  style={{ animation: "coach-message-in 0.2s ease-out both" }}
                >
                  {msg.role === "coach" && (
                    <Avatar className="size-7 shrink-0">
                      <AvatarFallback className="bg-primary/20 text-[10px] font-semibold text-primary">
                        AI
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div
                    className={cn(
                      "max-w-[85%] rounded-xl px-3 py-2 text-sm",
                      msg.role === "user"
                        ? "bg-primary text-white"
                        : "border border-[#ffffff08] bg-[#14141f] text-[#e2e2e8]",
                    )}
                  >
                    {renderMessageContent(msg.content)}
                  </div>
                </div>
              ))}

              {/* Typing indicator — waiting for first token (or initial session start) */}
              {showTypingIndicator && (
                <div className="flex gap-2">
                  <Avatar className="size-7 shrink-0">
                    <AvatarFallback className="bg-primary/20 text-[10px] font-semibold text-primary">
                      AI
                    </AvatarFallback>
                  </Avatar>
                  <div className="rounded-xl border border-[#ffffff08] bg-[#14141f]">
                    <TypingIndicator />
                  </div>
                </div>
              )}

              {/* Streaming message — tokens actively flowing in */}
              {showStreamingMessage && (
                <div className="flex gap-2">
                  <Avatar className="size-7 shrink-0">
                    <AvatarFallback className="bg-primary/20 text-[10px] font-semibold text-primary">
                      AI
                    </AvatarFallback>
                  </Avatar>
                  <div className="max-w-[85%] rounded-xl border border-[#ffffff08] bg-[#14141f] px-3 py-2">
                    <StreamingMessage
                      text={coachStream.currentText}
                      isStreaming={coachStream.isStreaming}
                    />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input */}
          <div className="border-t border-[#1e1e2e] p-3">
            {/* Quick action chip */}
            <div className="mb-2">
              <button
                type="button"
                onClick={() => handleSend("I'm stuck, can you give me a hint?")}
                disabled={isBusy || !sessionId}
                className="inline-flex items-center gap-1.5 rounded-full border border-[#ffffff0a] bg-[#14141f] px-2.5 py-1 text-[11px] text-[#6b6b80] transition-colors hover:border-primary/30 hover:text-[#a0a0b0] disabled:pointer-events-none disabled:opacity-40"
              >
                <Lightbulb className="size-3 text-[#fbbf24]" />
                I&apos;m stuck
              </button>
            </div>

            {/* Main input row */}
            <div className="flex items-end gap-2">
              <div className="relative flex-1">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask the coach… (Enter to send, Shift+Enter for newline, Esc to clear)"
                  rows={1}
                  aria-label="Message the coach"
                  aria-keyshortcuts="Enter"
                  disabled={isBusy || !sessionId}
                  className={cn(
                    "w-full resize-none rounded-xl border bg-[#0a0a0f] px-3 py-2 text-sm text-[#e2e2e8]",
                    "placeholder:text-[#4a4a5a]",
                    "transition-colors duration-150",
                    "border-[#1e1e2e] focus:border-primary/60 focus:outline-none focus:ring-2 focus:ring-primary/20",
                    "disabled:cursor-not-allowed disabled:opacity-40",
                    "max-h-[120px] overflow-y-auto",
                  )}
                />
                {/* Character count — appears only when approaching limit */}
                {input.length > 400 && (
                  <span
                    className={cn(
                      "absolute right-2.5 bottom-2 select-none font-mono text-[9px] tabular-nums",
                      input.length > 500 ? "text-destructive" : "text-muted-foreground",
                    )}
                    aria-live="polite"
                  >
                    {input.length}/500
                  </span>
                )}
              </div>
              <Button
                size="sm"
                aria-label="Send message"
                onClick={() => handleSend()}
                disabled={!input.trim() || isBusy || !sessionId}
                className="size-9 shrink-0 rounded-xl p-0"
              >
                <SendHorizontal className="size-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
