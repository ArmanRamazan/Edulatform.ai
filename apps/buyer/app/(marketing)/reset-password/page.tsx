"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { identity as identityApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/errors";
import { Header } from "@/components/Header";

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState<"form" | "success" | "error">("form");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Пароли не совпадают");
      return;
    }
    if (!token) {
      setError("Отсутствует токен");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await identityApi.resetPassword(token, password);
      setStatus("success");
    } catch (err) {
      setError(getErrorMessage(err, "Ошибка сброса пароля"));
      setStatus("error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-sm px-4 py-12">
      <h1 className="mb-6 text-center text-2xl font-bold">Новый пароль</h1>

      {status === "success" ? (
        <div className="text-center">
          <p className="mb-4 text-green-600">Пароль успешно изменён!</p>
          <Link href="/login" className="text-blue-600 hover:underline">
            Войти с новым паролем
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Новый пароль"
            required
            minLength={6}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          />
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Подтвердите пароль"
            required
            minLength={6}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Сохранение..." : "Сменить пароль"}
          </button>
        </form>
      )}
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <>
      <Header />
      <Suspense fallback={<main className="mx-auto max-w-sm px-4 py-12 text-center"><p className="text-gray-400">Загрузка...</p></main>}>
        <ResetPasswordContent />
      </Suspense>
    </>
  );
}
