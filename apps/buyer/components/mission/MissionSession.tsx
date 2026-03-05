"use client";

import { useState, useRef, useEffect, useCallback } from "react";
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
  useSendCoachMessage,
  useEndCoachSession,
  useCompleteMissionWithCoach,
  type CoachMessage,
  type CoachPhase,
} from "@/hooks/use-coach";
import { PhaseIndicator } from "./PhaseIndicator";
import { MissionComplete } from "./MissionComplete";
import type { Mission, CoachEndResponse, MissionBlueprint } from "@/lib/api";

interface MissionSessionProps {
  mission: Mission;
  token: string;
}

const PHASE_ORDER: CoachPhase[] = ["recap", "reading", "questions", "code_case", "wrap_up"];

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="size-1.5 rounded-full bg-muted-foreground"
          style={{
            animation: `typing-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  return (
    <pre className="overflow-x-auto rounded-lg bg-[#0a0a0f] p-4 font-mono text-xs leading-relaxed text-foreground">
      <code>{code}</code>
    </pre>
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
    return (
      <p key={i} className="whitespace-pre-wrap">
        {part}
      </p>
    );
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
                <Card key={i} className="border-border/50">
                  <CardContent className="p-4">
                    <p className="text-sm text-card-foreground">{q}</p>
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
            <div className="rounded-lg bg-secondary p-4 text-sm leading-relaxed text-card-foreground">
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
                <Card key={i} className="border-border/50">
                  <CardContent className="p-4">
                    <p className="mb-2 text-sm font-medium text-card-foreground">{q.question}</p>
                    {q.options && (
                      <div className="space-y-1.5">
                        {q.options.map((opt, j) => (
                          <div
                            key={j}
                            className="rounded-md bg-secondary px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-primary/10 hover:text-foreground"
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
  const sendMessage = useSendCoachMessage(token);
  const endSession = useEndCoachSession(token);
  const completeMission = useCompleteMissionWithCoach(token);

  const isTyping = sendMessage.isPending || startSession.isPending;

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

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

  function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || !sessionId || isTyping) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);

    sendMessage.mutate(
      { sessionId, message: msg },
      {
        onSuccess: (data) => {
          setMessages((prev) => [
            ...prev,
            { role: "coach", content: data.reply, phase: data.phase },
          ]);
          updatePhase(data.phase);
        },
        onError: (err) => {
          setMessages((prev) => [
            ...prev,
            { role: "coach", content: `Error: ${getErrorMessage(err)}` },
          ]);
        },
      },
    );
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

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (endResults) {
    return <MissionComplete results={endResults} />;
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <Card className="border-destructive/30">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
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
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-sm font-semibold text-card-foreground">
              {mission.blueprint?.concept_name ?? "Mission"}
            </h2>
            <p className="text-xs text-muted-foreground">
              {mission.mission_type}
            </p>
          </div>
          <PhaseIndicator currentPhase={phase} completedPhases={completedPhases} />
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="font-mono text-xs">
            {formatElapsed(elapsed)}
          </Badge>
          <Button
            size="sm"
            variant="outline"
            onClick={handleEnd}
            disabled={endSession.isPending || !sessionId}
          >
            End Session
          </Button>
        </div>
      </div>

      {/* Two-panel layout */}
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Left panel — Content */}
        <div className="flex-[3] overflow-y-auto border-b border-border md:border-b-0 md:border-r">
          <ContentArea phase={phase} blueprint={mission.blueprint} />
        </div>

        {/* Right panel — Coach Chat */}
        <div className="flex min-h-0 flex-[2] flex-col">
          {/* Messages */}
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-3">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={cn("flex gap-2", msg.role === "user" ? "justify-end" : "justify-start")}
                >
                  {msg.role === "coach" && (
                    <Avatar className="size-7 shrink-0">
                      <AvatarFallback className="bg-primary/20 text-xs text-primary">
                        AI
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div
                    className={cn(
                      "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-card text-card-foreground",
                    )}
                  >
                    {renderMessageContent(msg.content)}
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex gap-2">
                  <Avatar className="size-7 shrink-0">
                    <AvatarFallback className="bg-primary/20 text-xs text-primary">
                      AI
                    </AvatarFallback>
                  </Avatar>
                  <div className="rounded-lg bg-card">
                    <TypingIndicator />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input */}
          <div className="border-t border-border p-3">
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="shrink-0 text-xs text-muted-foreground"
                onClick={() => handleSend("I'm stuck, can you give me a hint?")}
                disabled={isTyping || !sessionId}
              >
                I&apos;m stuck
              </Button>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask the coach..."
                rows={1}
                disabled={isTyping || !sessionId}
                className="flex-1 resize-none rounded-lg border border-border bg-secondary px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none disabled:opacity-50"
              />
              <Button
                size="sm"
                onClick={() => handleSend()}
                disabled={!input.trim() || isTyping || !sessionId}
              >
                Send
              </Button>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes typing-dot {
          0%,
          60%,
          100% {
            opacity: 0.3;
            transform: scale(1);
          }
          30% {
            opacity: 1;
            transform: scale(1.3);
          }
        }
      `}</style>
    </div>
  );
}
