"use client";

import { useState } from "react";
import Link from "next/link";
import { identity as identityApi } from "@/lib/api";
import { Header } from "@/components/Header";

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
      // always show success to not reveal email existence
    } finally {
      setSent(true);
      setSubmitting(false);
    }
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-sm px-4 py-12">
        <h1 className="mb-6 text-center text-2xl font-bold">Восстановление пароля</h1>

        {sent ? (
          <div className="text-center">
            <p className="mb-4 text-gray-600">
              Если аккаунт с таким email существует, ссылка для сброса пароля была отправлена.
            </p>
            <Link href="/login" className="text-blue-600 hover:underline">
              Вернуться к входу
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Отправка..." : "Отправить ссылку"}
            </button>
            <p className="text-center text-sm text-gray-500">
              <Link href="/login" className="text-blue-600 hover:underline">
                Вернуться к входу
              </Link>
            </p>
          </form>
        )}
      </main>
    </>
  );
}
