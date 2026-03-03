"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";

export function HeroCTA() {
  const { user, loading } = useAuth();
  const isLoggedIn = !loading && !!user;

  if (loading) {
    return <div className="flex items-center justify-center gap-4 h-12" />;
  }

  return isLoggedIn ? (
    <>
      <Link
        href="/enrollments"
        className="rounded-lg bg-white px-6 py-3 font-semibold text-blue-700 transition hover:bg-blue-50"
      >
        Мои курсы
      </Link>
      {/* Plain <a> for same-page anchor — next/link does not handle fragment-only hrefs */}
      <a
        href="#catalog"
        className="rounded-lg border border-white px-6 py-3 font-semibold text-white transition hover:bg-white/10"
      >
        Найти курс
      </a>
    </>
  ) : (
    <>
      <Link
        href="/register"
        className="rounded-lg bg-white px-6 py-3 font-semibold text-blue-700 transition hover:bg-blue-50"
      >
        Начать бесплатно
      </Link>
      {/* Plain <a> for same-page anchor — next/link does not handle fragment-only hrefs */}
      <a
        href="#catalog"
        className="rounded-lg border border-white px-6 py-3 font-semibold text-white transition hover:bg-white/10"
      >
        Смотреть курсы
      </a>
    </>
  );
}
