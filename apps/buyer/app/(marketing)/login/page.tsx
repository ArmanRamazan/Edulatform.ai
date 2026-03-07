"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/errors";
import { Header } from "@/components/Header";

export default function LoginPage() {
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
      setError(getErrorMessage(err, "Login failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-sm px-4 py-12">
        <h1 className="mb-6 text-center text-2xl font-bold">Вход</h1>

        {error && (
          <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Пароль"
            required
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Вход..." : "Войти"}
          </button>
        </form>

        <p className="mt-3 text-center text-sm">
          <Link href="/forgot-password" className="text-blue-600 hover:underline">
            Забыли пароль?
          </Link>
        </p>
        <p className="mt-2 text-center text-sm text-gray-500">
          Нет аккаунта?{" "}
          <Link href="/register" className="text-blue-600 hover:underline">
            Зарегистрироваться
          </Link>
        </p>
      </main>
    </>
  );
}
