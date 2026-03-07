"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Zap, Mail, ArrowLeft, CheckCircle2 } from "lucide-react";
import { identity as identityApi } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await identityApi.forgotPassword(email);
    } catch {
      // Always show success — never reveal email existence
    } finally {
      setSent(true);
      setSubmitting(false);
    }
  }

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
          <AnimatePresence mode="wait">
            {sent ? (
              /* ── Success state ── */
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
                  Проверьте почту
                </h1>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: "#6b6b80" }}>
                  Если аккаунт с таким email существует, ссылка для сброса пароля была
                  отправлена.
                </p>
                <Link
                  href="/login"
                  className="mt-5 flex items-center gap-1.5 text-sm font-medium transition-colors"
                  style={{ color: "#7c5cfc" }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "#9b80fd")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "#7c5cfc")}
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Вернуться к входу
                </Link>
              </motion.div>
            ) : (
              /* ── Form state ── */
              <motion.div key="form" initial={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <div className="mb-6">
                  <h1
                    className="text-xl font-semibold tracking-tight"
                    style={{ color: "#e2e2e8", letterSpacing: "-0.01em" }}
                  >
                    Восстановление пароля
                  </h1>
                  <p className="mt-1 text-sm" style={{ color: "#6b6b80" }}>
                    Укажите email — пришлём ссылку для сброса
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-1.5">
                    <label
                      htmlFor="email"
                      className="block text-sm font-medium"
                      style={{ color: "#a0a0b0" }}
                    >
                      Email
                    </label>
                    <div className="relative">
                      <Mail
                        className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2"
                        style={{ color: "#6b6b80" }}
                      />
                      <input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@company.com"
                        required
                        autoComplete="email"
                        autoFocus
                        className="h-9 w-full rounded-lg pl-9 pr-3 text-sm transition-all placeholder:text-[#6b6b80]"
                        style={{
                          background: "#0a0a0f",
                          border: "1px solid rgba(255,255,255,0.1)",
                          color: "#e2e2e8",
                          outline: "none",
                        }}
                        onFocus={(e) => {
                          e.currentTarget.style.border = "1px solid #7c5cfc";
                          e.currentTarget.style.boxShadow =
                            "0 0 0 3px rgba(124,92,252,0.15)";
                        }}
                        onBlur={(e) => {
                          e.currentTarget.style.border =
                            "1px solid rgba(255,255,255,0.1)";
                          e.currentTarget.style.boxShadow = "none";
                        }}
                      />
                    </div>
                  </div>

                  <motion.button
                    type="submit"
                    disabled={submitting}
                    whileTap={{ scale: submitting ? 1 : 0.98 }}
                    className="mt-1 flex h-9 w-full items-center justify-center rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                    style={{ background: "#7c5cfc", color: "#ffffff" }}
                    onMouseEnter={(e) => {
                      if (!submitting) e.currentTarget.style.background = "#9b80fd";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "#7c5cfc";
                    }}
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                        Отправка...
                      </>
                    ) : (
                      "Отправить ссылку"
                    )}
                  </motion.button>
                </form>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Back link */}
        {!sent && (
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
        )}
      </motion.div>
    </main>
  );
}
