"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Zap, AlertCircle, CheckCircle2, ArrowLeft } from "lucide-react";
import { identity as identityApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/errors";

const inputBase = {
  background: "#0a0a0f",
  border: "1px solid rgba(255,255,255,0.1)",
  color: "#e2e2e8",
  outline: "none",
} as const;

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState<"form" | "success">("form");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Inline match validation — only on confirm blur
  const mismatch = confirm.length > 0 && password !== confirm;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Пароли не совпадают");
      return;
    }
    if (!token) {
      setError("Отсутствует токен сброса");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await identityApi.resetPassword(token, password);
      setStatus("success");
    } catch (err) {
      setError(getErrorMessage(err, "Ошибка сброса пароля. Попробуйте ещё раз"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AnimatePresence mode="wait">
      {status === "success" ? (
        <motion.div
          key="success"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center py-2 text-center"
        >
          <div
            className="mb-4 flex h-12 w-12 items-center justify-center rounded-full"
            style={{
              background: "rgba(52,211,153,0.1)",
              border: "1px solid rgba(52,211,153,0.25)",
            }}
          >
            <CheckCircle2 className="h-6 w-6" style={{ color: "#34d399" }} />
          </div>
          <h1
            className="text-lg font-semibold"
            style={{ color: "#e2e2e8", letterSpacing: "-0.01em" }}
          >
            Пароль изменён
          </h1>
          <p className="mt-2 text-sm" style={{ color: "#6b6b80" }}>
            Войдите с новым паролем
          </p>
          <Link
            href="/login"
            className="mt-5 flex h-9 items-center justify-center rounded-lg px-5 text-sm font-medium transition-colors"
            style={{ background: "#7c5cfc", color: "#ffffff" }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLElement).style.background = "#9b80fd")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLElement).style.background = "#7c5cfc")
            }
          >
            Войти
          </Link>
        </motion.div>
      ) : (
        <motion.div key="form" initial={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <div className="mb-6">
            <h1
              className="text-xl font-semibold tracking-tight"
              style={{ color: "#e2e2e8", letterSpacing: "-0.01em" }}
            >
              Новый пароль
            </h1>
            <p className="mt-1 text-sm" style={{ color: "#6b6b80" }}>
              Придумайте надёжный пароль
            </p>
          </div>

          {/* Error banner */}
          {error && (
            <motion.div
              id="reset-error"
              role="alert"
              aria-live="polite"
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="mb-4 flex items-start gap-2.5 rounded-lg px-3 py-2.5"
              style={{
                background: "rgba(248,113,113,0.08)",
                border: "1px solid rgba(248,113,113,0.2)",
              }}
            >
              <AlertCircle
                className="mt-0.5 h-3.5 w-3.5 shrink-0"
                style={{ color: "#f87171" }}
              />
              <p className="text-sm leading-snug" style={{ color: "#f87171" }}>
                {error}
              </p>
            </motion.div>
          )}

          <form
            onSubmit={handleSubmit}
            className="space-y-4"
            aria-describedby={error ? "reset-error" : undefined}
          >
            {/* New password */}
            <div className="space-y-1.5">
              <label
                htmlFor="password"
                className="block text-sm font-medium"
                style={{ color: "#a0a0b0" }}
              >
                Новый пароль
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Минимум 6 символов"
                required
                minLength={6}
                autoComplete="new-password"
                autoFocus
                className="h-9 w-full rounded-lg px-3 text-sm transition-all placeholder:text-[#6b6b80]"
                style={inputBase}
                onFocus={(e) => {
                  e.currentTarget.style.border = "1px solid #7c5cfc";
                  e.currentTarget.style.boxShadow = "0 0 0 3px rgba(124,92,252,0.15)";
                }}
                onBlur={(e) => {
                  e.currentTarget.style.border = "1px solid rgba(255,255,255,0.1)";
                  e.currentTarget.style.boxShadow = "none";
                }}
              />
            </div>

            {/* Confirm password */}
            <div className="space-y-1.5">
              <label
                htmlFor="confirm"
                className="block text-sm font-medium"
                style={{ color: "#a0a0b0" }}
              >
                Подтвердите пароль
              </label>
              <input
                id="confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Повторите пароль"
                required
                minLength={6}
                autoComplete="new-password"
                aria-invalid={mismatch}
                aria-describedby={mismatch ? "confirm-error" : undefined}
                className="h-9 w-full rounded-lg px-3 text-sm transition-all placeholder:text-[#6b6b80]"
                style={{
                  ...inputBase,
                  border: mismatch
                    ? "1px solid rgba(248,113,113,0.5)"
                    : "1px solid rgba(255,255,255,0.1)",
                }}
                onFocus={(e) => {
                  if (!mismatch) {
                    e.currentTarget.style.border = "1px solid #7c5cfc";
                    e.currentTarget.style.boxShadow =
                      "0 0 0 3px rgba(124,92,252,0.15)";
                  }
                }}
                onBlur={(e) => {
                  e.currentTarget.style.boxShadow = "none";
                  e.currentTarget.style.border = mismatch
                    ? "1px solid rgba(248,113,113,0.5)"
                    : "1px solid rgba(255,255,255,0.1)";
                }}
              />
              {/* Inline mismatch hint */}
              <AnimatePresence>
                {mismatch && (
                  <motion.p
                    id="confirm-error"
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.2 }}
                    className="text-xs"
                    style={{ color: "#f87171" }}
                  >
                    Пароли не совпадают
                  </motion.p>
                )}
              </AnimatePresence>
            </div>

            <motion.button
              type="submit"
              disabled={submitting || mismatch}
              whileTap={{ scale: submitting ? 1 : 0.98 }}
              className="mt-1 flex h-9 w-full items-center justify-center rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60"
              style={{ background: "#7c5cfc", color: "#ffffff" }}
              onMouseEnter={(e) => {
                if (!submitting && !mismatch)
                  e.currentTarget.style.background = "#9b80fd";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "#7c5cfc";
              }}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                  Сохранение...
                </>
              ) : (
                "Сменить пароль"
              )}
            </motion.button>
          </form>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function ResetPasswordPage() {
  return (
    <main
      className="relative flex min-h-screen flex-col items-center justify-center px-4"
      style={{ background: "#07070b" }}
    >
      {/* Atmospheric violet glow */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <div
          className="absolute left-1/2 top-0 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/4 rounded-full"
          style={{
            background:
              "radial-gradient(ellipse at center, rgba(124,92,252,0.12) 0%, transparent 70%)",
          }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 w-full max-w-sm"
      >
        {/* Brand mark */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35, delay: 0.05 }}
          className="mb-8 flex flex-col items-center gap-3"
        >
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl"
            style={{
              background: "rgba(124,92,252,0.15)",
              border: "1px solid rgba(124,92,252,0.3)",
            }}
          >
            <Zap className="h-5 w-5" style={{ color: "#7c5cfc" }} />
          </div>
          <p
            className="text-xs font-medium tracking-widest uppercase"
            style={{ color: "#6b6b80" }}
          >
            KnowledgeOS
          </p>
        </motion.div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-xl p-6"
          style={{
            background: "#14141f",
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <Suspense
            fallback={
              <div className="flex flex-col items-center py-2">
                <Loader2
                  className="h-5 w-5 animate-spin"
                  style={{ color: "#7c5cfc" }}
                />
              </div>
            }
          >
            <ResetPasswordContent />
          </Suspense>
        </motion.div>

        {/* Back link */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.25 }}
          className="mt-4 text-center text-sm"
          style={{ color: "#6b6b80" }}
        >
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 font-medium transition-colors"
            style={{ color: "#7c5cfc" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#9b80fd")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#7c5cfc")}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Вернуться к входу
          </Link>
        </motion.p>
      </motion.div>
    </main>
  );
}
