"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { courses } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/errors";

export default function NewCoursePage() {
  const router = useRouter();
  const { token, user, loading } = useAuth();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isFree, setIsFree] = useState(true);
  const [price, setPrice] = useState("");
  const [duration, setDuration] = useState("");
  const [level, setLevel] = useState("beginner");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!loading && (!user || user.role !== "teacher" || !user.is_verified)) {
    const isUnverifiedTeacher = user?.role === "teacher" && !user.is_verified;
    return (
      <main className="mx-auto max-w-sm px-4 py-12 text-center">
        {isUnverifiedTeacher ? (
          <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
            Ваш аккаунт ожидает верификации. После одобрения администратором вы сможете создавать курсы.
          </div>
        ) : (
          <p className="mb-4 text-gray-500">
            Создавать курсы могут только верифицированные преподаватели
          </p>
        )}
        <Link href="/" className="text-blue-600 hover:underline">
          На главную
        </Link>
      </main>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError("");
    setSubmitting(true);
    try {
      const course = await courses.create(token, {
        title,
        description,
        is_free: isFree,
        price: isFree ? undefined : parseFloat(price),
        duration_minutes: parseInt(duration, 10) || 0,
        level,
      });
      router.push(`/courses/${course.id}/edit`);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to create"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 py-6">
        <Link href="/" className="mb-4 inline-block text-sm text-blue-600 hover:underline">
          &larr; Назад
        </Link>
        <h1 className="mb-6 text-2xl font-bold">Новый курс</h1>

        {error && (
          <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Название курса"
            required
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          />
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Описание"
            rows={4}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          />

          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          >
            <option value="beginner">Начальный</option>
            <option value="intermediate">Средний</option>
            <option value="advanced">Продвинутый</option>
          </select>

          <input
            type="number"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="Длительность (мин.)"
            min="0"
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          />

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isFree}
              onChange={(e) => setIsFree(e.target.checked)}
              className="text-blue-600"
            />
            <span className="text-sm">Бесплатный курс</span>
          </label>

          {!isFree && (
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="Цена"
              min="0.01"
              step="0.01"
              required
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
            />
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Создание..." : "Создать курс"}
          </button>
        </form>
      </main>
  );
}
