"use client";

/**
 * Animated typing indicator shown while coach is generating a response.
 * Three violet dots with a staggered bounce + glow at peak opacity.
 * Keyframes live in globals.css (coach-typing-dot, coach-indicator-in).
 */
export function TypingIndicator() {
  return (
    <div
      role="status"
      aria-label="Coach is thinking"
      className="flex items-center gap-[5px] px-3 py-2.5"
      style={{ animation: "coach-indicator-in 0.2s ease-out both" }}
    >
      {/* Screen-reader-only label so assistive tech announces the loading state */}
      <span className="sr-only">Coach is thinking…</span>

      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="size-1.5 rounded-full bg-primary"
          style={{
            animationName: "coach-typing-dot",
            animationDuration: "1.3s",
            animationTimingFunction: "ease-in-out",
            animationDelay: `${i * 0.16}s`,
            animationIterationCount: "infinite",
            animationFillMode: "both",
          }}
        />
      ))}
    </div>
  );
}
