"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion, type Variants } from "framer-motion";
import { Loader2, AlertCircle, Zap, BookOpen, GraduationCap } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/errors";
import { identity as identityApi } from "@/lib/api";

const inputStyle = {
  background: "#0a0a0f",
  border: "1px solid rgba(255,255,255,0.1)",
  color: "#e2e2e8",
  outline: "none",
} as const;

const inputFocusStyle = {
  border: "1px solid #7c5cfc",
  boxShadow: "0 0 0 3px rgba(124,92,252,0.15)",
};

const inputBlurStyle = {
  border: "1px solid rgba(255,255,255,0.1)",
  boxShadow: "none",
};

function StyledInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="h-9 w-full rounded-lg px-3 text-sm transition-all placeholder:text-[#6b6b80]"
      style={inputStyle}
      onFocus={(e) => {
        Object.assign(e.currentTarget.style, inputFocusStyle);
        props.onFocus?.(e);
      }}
      onBlur={(e) => {
        Object.assign(e.currentTarget.style, inputBlurStyle);
        props.onBlur?.(e);
      }}
    />
  );
}

const containerVariants: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("student");
  const [referralCode, setReferralCode] = useState(searchParams.get("ref") ?? "");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(email, password, name, role);
      if (referralCode.trim()) {
        const token = localStorage.getItem("token");
        if (token) {
          try {
            await identityApi.applyReferralCode(token, { referral_code: referralCode.trim() });
          } catch {
            // Referral apply failure is non-blocking
          }
        }
      }
      router.push("/onboarding");
    } catch (err) {
      setError(getErrorMessage(err, "Не удалось создать аккаунт"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main
      className="relative flex min-h-screen flex-col items-center justify-center px-4 py-8"
      style={{ background: "#07070b" }}
    >
      {/* Atmospheric violet glow */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <div
          className="absolute left-1/2 top-0 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/4 rounded-full"
          style={{
            background:
              "radial-gradient(ellipse at center, rgba(124,92,252,0.1) 0%, transparent 70%)",
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
          <p className="text-xs font-medium tracking-widest uppercase" style={{ color: "#6b6b80" }}>
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
          <div className="mb-5">
            <h1
              className="text-xl font-semibold"
              style={{ color: "#e2e2e8", letterSpacing: "-0.01em" }}
            >
              Создать аккаунт
            </h1>
            <p className="mt-1 text-sm" style={{ color: "#6b6b80" }}>
              Начните работу с KnowledgeOS
            </p>
          </div>

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="mb-4 flex items-start gap-2.5 rounded-lg px-3 py-2.5"
              style={{
                background: "rgba(248,113,113,0.08)",
                border: "1px solid rgba(248,113,113,0.2)",
              }}
            >
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" style={{ color: "#f87171" }} />
              <p className="text-sm leading-snug" style={{ color: "#f87171" }}>
                {error}
              </p>
            </motion.div>
          )}

          <motion.form
            onSubmit={handleSubmit}
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-4"
          >
            {/* Name */}
            <motion.div variants={itemVariants} className="space-y-1.5">
              <label htmlFor="name" className="block text-sm font-medium" style={{ color: "#a0a0b0" }}>
                Имя
              </label>
              <StyledInput
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Иван Иванов"
                required
                autoComplete="name"
                autoFocus
              />
            </motion.div>

            {/* Email */}
            <motion.div variants={itemVariants} className="space-y-1.5">
              <label htmlFor="email" className="block text-sm font-medium" style={{ color: "#a0a0b0" }}>
                Email
              </label>
              <StyledInput
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                autoComplete="email"
              />
            </motion.div>

            {/* Password */}
            <motion.div variants={itemVariants} className="space-y-1.5">
              <label htmlFor="password" className="block text-sm font-medium" style={{ color: "#a0a0b0" }}>
                Пароль
              </label>
              <StyledInput
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Минимум 6 символов"
                required
                minLength={6}
                autoComplete="new-password"
              />
            </motion.div>

            {/* Referral code */}
            <motion.div variants={itemVariants} className="space-y-1.5">
              <label htmlFor="referral" className="block text-sm font-medium" style={{ color: "#a0a0b0" }}>
                Реферальный код{" "}
                <span className="font-normal" style={{ color: "#6b6b80" }}>
                  (необязательно)
                </span>
              </label>
              <StyledInput
                id="referral"
                type="text"
                value={referralCode}
                onChange={(e) => setReferralCode(e.target.value)}
                placeholder="XXXXX"
                autoComplete="off"
              />
            </motion.div>

            {/* Role selector */}
            <motion.div variants={itemVariants} className="space-y-2">
              <p className="text-sm font-medium" style={{ color: "#a0a0b0" }}>
                Роль
              </p>
              <div className="grid grid-cols-2 gap-2">
                {(
                  [
                    { value: "student", label: "Студент", Icon: GraduationCap },
                    { value: "teacher", label: "Преподаватель", Icon: BookOpen },
                  ] as const
                ).map(({ value, label, Icon }) => {
                  const active = role === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setRole(value)}
                      className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all"
                      style={{
                        background: active ? "rgba(124,92,252,0.12)" : "#0a0a0f",
                        border: active
                          ? "1px solid rgba(124,92,252,0.35)"
                          : "1px solid rgba(255,255,255,0.08)",
                        color: active ? "#9b80fd" : "#6b6b80",
                      }}
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      {label}
                    </button>
                  );
                })}
              </div>
            </motion.div>

            {/* Submit */}
            <motion.div variants={itemVariants}>
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
                    Создание аккаунта...
                  </>
                ) : (
                  "Создать аккаунт"
                )}
              </motion.button>
            </motion.div>
          </motion.form>
        </motion.div>

        {/* Footer link */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="mt-4 text-center text-sm"
          style={{ color: "#6b6b80" }}
        >
          Уже есть аккаунт?{" "}
          <Link
            href="/login"
            className="font-medium transition-colors"
            style={{ color: "#7c5cfc" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#9b80fd")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#7c5cfc")}
          >
            Войти
          </Link>
        </motion.p>
      </motion.div>
    </main>
  );
}

export default function RegisterPage() {
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
      <RegisterForm />
    </Suspense>
  );
}
