"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Loader2, AlertCircle, Zap } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/errors";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      const redirect = searchParams.get("redirect");
      router.push(redirect ?? "/dashboard");
    } catch (err) {
      setError(getErrorMessage(err, "Неверный email или пароль"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main
      className="relative flex min-h-screen flex-col items-center justify-center px-4"
      style={{ background: "#07070b" }}
    >
      {/* Atmospheric violet radial glow — purely decorative */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
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
          <div className="text-center">
            <p className="text-xs font-medium tracking-widest uppercase" style={{ color: "#6b6b80" }}>
              KnowledgeOS
            </p>
          </div>
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
          <div className="mb-6">
            <h1
              className="text-xl font-semibold tracking-tight"
              style={{ color: "#e2e2e8", letterSpacing: "-0.01em" }}
            >
              Добро пожаловать
            </h1>
            <p className="mt-1 text-sm" style={{ color: "#6b6b80" }}>
              Войдите в свой аккаунт
            </p>
          </div>

          {/* Error banner */}
          {error && (
            <motion.div
              id="login-error"
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
            aria-describedby={error ? "login-error" : undefined}
          >
            {/* Email */}
            <div className="space-y-1.5">
              <label
                htmlFor="email"
                className="block text-sm font-medium"
                style={{ color: "#a0a0b0" }}
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                autoComplete="email"
                autoFocus
                className="h-9 w-full rounded-lg px-3 text-sm transition-colors placeholder:text-[#6b6b80]"
                style={{
                  background: "#0a0a0f",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#e2e2e8",
                  outline: "none",
                }}
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

            {/* Password */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="block text-sm font-medium"
                  style={{ color: "#a0a0b0" }}
                >
                  Пароль
                </label>
                <Link
                  href="/forgot-password"
                  className="text-xs transition-colors"
                  style={{ color: "#7c5cfc" }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "#9b80fd")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "#7c5cfc")}
                >
                  Забыли пароль?
                </Link>
              </div>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="current-password"
                className="h-9 w-full rounded-lg px-3 text-sm transition-colors placeholder:text-[#6b6b80]"
                style={{
                  background: "#0a0a0f",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#e2e2e8",
                  outline: "none",
                }}
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

            {/* Submit */}
            <motion.button
              type="submit"
              disabled={submitting}
              whileTap={{ scale: submitting ? 1 : 0.98 }}
              className="relative mt-1 flex h-9 w-full items-center justify-center rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60"
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
                  Вход...
                </>
              ) : (
                "Войти"
              )}
            </motion.button>
          </form>
        </motion.div>

        {/* Footer link */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.25 }}
          className="mt-4 text-center text-sm"
          style={{ color: "#6b6b80" }}
        >
          Нет аккаунта?{" "}
          <Link
            href="/register"
            className="font-medium transition-colors"
            style={{ color: "#7c5cfc" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#9b80fd")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#7c5cfc")}
          >
            Зарегистрироваться
          </Link>
        </motion.p>
      </motion.div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main
          className="flex min-h-screen items-center justify-center"
          style={{ background: "#07070b" }}
        >
          <Loader2 className="h-5 w-5 animate-spin" style={{ color: "#7c5cfc" }} />
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
