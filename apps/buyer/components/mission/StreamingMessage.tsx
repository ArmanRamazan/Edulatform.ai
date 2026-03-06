"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

interface StreamingMessageProps {
  text: string;
  isStreaming: boolean;
  className?: string;
}

/**
 * Code block with a language label strip and one-click copy button.
 * Matches Dark Knowledge aesthetics — near-black bg, violet accent on copy confirm.
 */
function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    void navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [code]);

  return (
    <div className="my-2 overflow-hidden rounded-lg border border-[#ffffff08]">
      {/* Top bar: language label + copy button */}
      <div className="flex items-center justify-between border-b border-[#ffffff08] bg-[#07070b] px-3 py-1.5">
        <span className="font-mono text-[10px] tracking-widest text-[#6b6b80] uppercase">
          {lang || "code"}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={copied ? "Copied!" : "Copy code"}
          className={cn(
            "flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[10px] transition-all duration-150",
            copied
              ? "text-[#34d399]"
              : "text-[#6b6b80] hover:bg-[#ffffff08] hover:text-[#a0a0b0]",
          )}
        >
          {copied ? (
            <Check className="size-2.5" aria-hidden="true" />
          ) : (
            <Copy className="size-2.5" aria-hidden="true" />
          )}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto bg-[#07070b] p-4 font-mono text-xs leading-relaxed text-[#e2e2e8]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function renderCompleteText(text: string) {
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const lines = part.slice(3, -3).split("\n");
      const lang = lines[0]?.trim();
      const code = lang ? lines.slice(1).join("\n") : lines.join("\n");
      return <CodeBlock key={i} code={code} lang={lang} />;
    }
    // Guard: skip empty segments that come from the split
    const trimmed = part.trim();
    return trimmed ? (
      <p key={i} className="whitespace-pre-wrap text-[#e2e2e8]">
        {part}
      </p>
    ) : null;
  });
}

/**
 * Renders a coach message that grows token by token during streaming.
 * Shows a blinking violet cursor while streaming; disappears on completion.
 * Once done, re-renders with full code-block + language-badge formatting.
 *
 * Keyframes (coach-cursor-blink, coach-message-in) live in globals.css.
 */
export function StreamingMessage({ text, isStreaming, className }: StreamingMessageProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Scroll the message end into view as new tokens arrive
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [text]);

  return (
    <div
      className={cn("text-sm", className)}
      // Announce streaming content to screen readers as it updates
      aria-live="polite"
      aria-atomic="false"
      aria-busy={isStreaming}
      style={{ animation: "coach-message-in 0.18s ease-out both" }}
    >
      {isStreaming ? (
        // During streaming: plain pre-wrap text + blinking violet cursor.
        // We deliberately avoid mid-stream code-block detection to prevent
        // layout thrashing while tokens arrive one word at a time.
        <p className="whitespace-pre-wrap text-[#e2e2e8]">
          {text}
          <span
            className="ml-0.5 inline-block h-[1em] w-[2px] translate-y-px rounded-[1px] bg-primary align-text-bottom"
            aria-hidden="true"
            style={{
              animationName: "coach-cursor-blink",
              animationDuration: "0.9s",
              animationTimingFunction: "step-end",
              animationIterationCount: "infinite",
            }}
          />
        </p>
      ) : (
        // Complete: full code-block rendering. Gentle fade-in settle so the
        // transition from raw streaming text to formatted output feels intentional.
        <div
          className="space-y-2"
          style={{ animation: "coach-stream-settle 0.35s ease-out both" }}
        >
          {renderCompleteText(text)}
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
