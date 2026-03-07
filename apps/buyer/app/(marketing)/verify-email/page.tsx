"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Zap, CheckCircle2, AlertCircle, ArrowLeft } from "lucide-react";
import { identity as identityApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/errors";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("Отсутствует токен верификации");
      return;
    }
    identityApi
      .verifyEmail(token)
      .then(() => setStatus("success"))
      .catch((e) => {
        setStatus("error");
        setError(getErrorMessage(e, "Ссылка недействительна или срок действия истёк"));
      });
  }, [token]);

  return (
    <AnimatePresence mode="wait">
      {status === "loading" && (
        <motion.div
          key="loading"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex flex-col items-center py-2 text-center"
        >
          {/* Skeleton brand icon */}
          <div
            className="mb-4 flex h-12 w-12 items-center justify-center rounded-full"
            style={{
              background: "rgba(124,92,252,0.08)",
              border: "1px solid rgba(124,92,252,0.15)",
            }}
          >
            <Loader2 className="h-5 w-5 animate-spin" style={{ color: "#7c5cfc" }} />
          </div>
          {/* Skeleton lines */}
          <div
            className="mb-2 h-4 w-40 animate-pulse rounded"
            style={{ background: "rgba(255,255,255,0.06)" }}
          />
          <div
            className="h-3 w-56 animate-pulse rounded"
            style={{ background: "rgba(255,255,255,0.04)" }}
          />
        </motion.div>
      )}

      {status === "success" && (
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
            Email подтверждён
          </h1>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "#6b6b80" }}>
            Ваш адрес электронной почты успешно верифицирован.
          </p>
          <Link
            href="/dashboard"
            className="mt-5 flex h-9 items-center justify-center rounded-lg px-5 text-sm font-medium transition-colors"
            style={{ background: "#7c5cfc", color: "#ffffff" }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLElement).style.background = "#9b80fd")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLElement).style.background = "#7c5cfc")
            }
          >
            Перейти в дашборд
          </Link>
        </motion.div>
      )}

      {status === "error" && (
        <motion.div
          key="error"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center py-2 text-center"
        >
          <div
            className="mb-4 flex h-12 w-12 items-center justify-center rounded-full"
            style={{
              background: "rgba(248,113,113,0.08)",
              border: "1px solid rgba(248,113,113,0.2)",
            }}
          >
            <AlertCircle className="h-6 w-6" style={{ color: "#f87171" }} />
          </div>
          <h1
            className="text-lg font-semibold"
            style={{ color: "#e2e2e8", letterSpacing: "-0.01em" }}
          >
            Верификация не удалась
          </h1>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "#6b6b80" }}>
            {error}
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
      )}
    </AnimatePresence>
  );
}

export default function VerifyEmailPage() {
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
              <div className="flex flex-col items-center py-2 text-center">
                <div
                  className="mb-4 flex h-12 w-12 items-center justify-center rounded-full"
                  style={{
                    background: "rgba(124,92,252,0.08)",
                    border: "1px solid rgba(124,92,252,0.15)",
                  }}
                >
                  <Loader2
                    className="h-5 w-5 animate-spin"
                    style={{ color: "#7c5cfc" }}
                  />
                </div>
                <div
                  className="mb-2 h-4 w-40 animate-pulse rounded"
                  style={{ background: "rgba(255,255,255,0.06)" }}
                />
                <div
                  className="h-3 w-56 animate-pulse rounded"
                  style={{ background: "rgba(255,255,255,0.04)" }}
                />
              </div>
            }
          >
            <VerifyEmailContent />
          </Suspense>
        </motion.div>
      </motion.div>
    </main>
  );
}
