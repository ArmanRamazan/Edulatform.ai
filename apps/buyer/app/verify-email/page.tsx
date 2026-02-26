"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { identity as identityApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/errors";
import { Header } from "@/components/Header";

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
        setError(getErrorMessage(e, "Ошибка верификации"));
      });
  }, [token]);

  return (
    <main className="mx-auto max-w-sm px-4 py-12 text-center">
      {status === "loading" && (
        <p className="text-gray-400">Проверка токена...</p>
      )}
      {status === "success" && (
        <div>
          <h1 className="mb-4 text-2xl font-bold text-green-600">Email подтверждён!</h1>
          <p className="mb-4 text-gray-600">Ваш email успешно верифицирован.</p>
          <Link href="/" className="text-blue-600 hover:underline">
            На главную
          </Link>
        </div>
      )}
      {status === "error" && (
        <div>
          <h1 className="mb-4 text-2xl font-bold text-red-600">Ошибка</h1>
          <p className="mb-4 text-gray-600">{error}</p>
          <Link href="/" className="text-blue-600 hover:underline">
            На главную
          </Link>
        </div>
      )}
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <>
      <Header />
      <Suspense fallback={<main className="mx-auto max-w-sm px-4 py-12 text-center"><p className="text-gray-400">Загрузка...</p></main>}>
        <VerifyEmailContent />
      </Suspense>
    </>
  );
}
