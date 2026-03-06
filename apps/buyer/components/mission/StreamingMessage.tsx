"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface StreamingMessageProps {
  text: string;
  isStreaming: boolean;
  className?: string;
}

function CodeBlock({ code }: { code: string }) {
  return (
    <pre className="my-2 overflow-x-auto rounded-lg bg-[#0a0a0f] p-4 font-mono text-xs leading-relaxed text-foreground">
      <code>{code}</code>
    </pre>
  );
}

function renderCompleteText(text: string) {
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const lines = part.slice(3, -3).split("\n");
      const lang = lines[0]?.trim();
      const code = lang ? lines.slice(1).join("\n") : lines.join("\n");
      return <CodeBlock key={i} code={code} />;
    }
    return part ? (
      <p key={i} className="whitespace-pre-wrap">
        {part}
      </p>
    ) : null;
  });
}

/**
 * Renders a coach message that grows token by token during streaming.
 * Shows a blinking violet cursor while streaming; disappears on completion.
 * Once done, re-renders with full code-block formatting.
 */
export function StreamingMessage({ text, isStreaming, className }: StreamingMessageProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Scroll the message end into view as new tokens arrive
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [text]);

  return (
    <div className={cn("text-sm", className)}>
      {isStreaming ? (
        // During streaming: plain pre-formatted text + blinking cursor
        // Avoids layout jumps from mid-stream code block detection
        <p className="whitespace-pre-wrap">
          {text}
          <span
            className="ml-0.5 inline-block h-[1em] w-[2px] translate-y-px rounded-sm bg-primary align-text-bottom"
            style={{ animation: "coach-cursor-blink 1s step-end infinite" }}
          />
        </p>
      ) : (
        // Complete: full code-block rendering with JetBrains Mono for code
        <div className="space-y-1">{renderCompleteText(text)}</div>
      )}
      <div ref={endRef} />
      <style>{`
        @keyframes coach-cursor-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}
