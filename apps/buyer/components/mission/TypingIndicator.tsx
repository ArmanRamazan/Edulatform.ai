"use client";

/**
 * Animated typing indicator shown while coach is generating a response.
 * Three violet dots with a staggered bounce + glow at peak opacity.
 * A muted "Thinking" label anchors the visual for sighted users.
 * Ambient glow pulses on the container to signal active generation.
 * Keyframes live in globals.css (coach-typing-dot, coach-indicator-in, typing-ambient-glow).
 */
export function TypingIndicator() {
  return (
    <div
      role="status"
      aria-label="Coach is thinking"
      className="flex items-center gap-2.5 rounded-xl px-3 py-2.5"
      style={{
        animation: "coach-indicator-in 0.2s ease-out both, typing-ambient-glow 2.4s ease-in-out 0.4s infinite",
      }}
    >
      {/* Screen-reader-only label so assistive tech announces the loading state */}
      <span className="sr-only">Coach is thinking…</span>

      {/* Visible "Thinking" label — subtle, muted, gives context without noise */}
      <span
        className="select-none font-mono text-[10px] uppercase tracking-widest text-[#6b6b80]"
        aria-hidden="true"
      >
        Thinking
      </span>

      {/* Dot cluster */}
      <div className="flex items-center gap-[5px]">
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
    </div>
  );
}
