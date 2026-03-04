"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useCreateCourse } from "@/hooks/use-courses";
import { modules as modulesApi, lessons as lessonsApi, type OutlineModule } from "@/lib/api";
import { AIOutlineModal } from "@/components/AIOutlineModal";

interface LocalLesson {
  title: string;
  description: string;
  estimatedMinutes: number;
}

interface LocalModule {
  title: string;
  description: string;
  lessons: LocalLesson[];
}

export default function NewCoursePage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const createCourse = useCreateCourse(token);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [level, setLevel] = useState<"beginner" | "intermediate" | "advanced">("beginner");
  const [isFree, setIsFree] = useState(true);
  const [price, setPrice] = useState("");
  const [courseModules, setCourseModules] = useState<LocalModule[]>([]);
  const [showAIModal, setShowAIModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
      </div>
    );
  }

  if (!token) {
    router.push("/dashboard");
    return null;
  }

  const handleApplyOutline = (modules: OutlineModule[]) => {
    const mapped: LocalModule[] = modules.map((m) => ({
      title: m.title,
      description: m.description,
      lessons: m.lessons.map((l) => ({
        title: l.title,
        description: l.description,
        estimatedMinutes: l.estimated_duration_minutes,
      })),
    }));
    setCourseModules(mapped);
    setShowAIModal(false);
  };

  const totalDuration = courseModules.reduce(
    (sum, m) => sum + m.lessons.reduce((s, l) => s + l.estimatedMinutes, 0),
    0,
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setError("");
    setSaving(true);

    try {
      const course = await createCourse.mutateAsync({
        title: title.trim(),
        description: description.trim(),
        level,
        is_free: isFree,
        price: isFree ? null : Number(price) || null,
        duration_minutes: totalDuration || 0,
        category_id: null,
      });

      for (let mi = 0; mi < courseModules.length; mi++) {
        const mod = courseModules[mi];
        const createdModule = await modulesApi.create(token, course.id, {
          title: mod.title,
          order: mi,
        });

        for (let li = 0; li < mod.lessons.length; li++) {
          const lesson = mod.lessons[li];
          await lessonsApi.create(token, createdModule.id, {
            title: lesson.title,
            content: lesson.description,
            video_url: null,
            duration_minutes: lesson.estimatedMinutes,
            order: li,
          });
        }
      }

      router.push(`/courses/${course.id}/edit`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания курса");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">
          &larr; Назад
        </Link>
        <h1 className="text-2xl font-bold">Создать курс</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 font-semibold">Основная информация</h2>

          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Название</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Название курса"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Описание</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Опишите ваш курс"
                rows={3}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex gap-4">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium">Уровень</label>
                <select
                  value={level}
                  onChange={(e) => setLevel(e.target.value as typeof level)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                >
                  <option value="beginner">Начинающий</option>
                  <option value="intermediate">Средний</option>
                  <option value="advanced">Продвинутый</option>
                </select>
              </div>

              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium">Цена</label>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={isFree}
                      onChange={(e) => setIsFree(e.target.checked)}
                    />
                    Бесплатный
                  </label>
                  {!isFree && (
                    <input
                      type="number"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      placeholder="Цена в ₽"
                      min={0}
                      className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Модули и уроки</h2>
            <button
              type="button"
              onClick={() => setShowAIModal(true)}
              className="rounded-lg border border-purple-300 bg-purple-50 px-3 py-1.5 text-sm font-medium text-purple-700 hover:bg-purple-100"
            >
              Сгенерировать структуру с помощью AI
            </button>
          </div>

          {courseModules.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center">
              <p className="text-sm text-gray-500">
                Модулей пока нет. Используйте AI для генерации структуры курса или добавьте модули после создания.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {courseModules.map((mod, mi) => (
                <div key={mi} className="rounded-lg border border-gray-200 p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-sm font-semibold">
                        Модуль {mi + 1}: {mod.title}
                      </h3>
                      <p className="text-xs text-gray-500">{mod.description}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setCourseModules((prev) => prev.filter((_, i) => i !== mi))}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Удалить
                    </button>
                  </div>
                  <ul className="mt-2 space-y-1">
                    {mod.lessons.map((lesson, li) => (
                      <li key={li} className="text-xs text-gray-600">
                        {li + 1}. {lesson.title}
                        <span className="ml-1 text-gray-400">~{lesson.estimatedMinutes} мин</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              <p className="text-xs text-gray-500">
                Всего: {courseModules.reduce((s, m) => s + m.lessons.length, 0)} уроков, ~{totalDuration} мин
              </p>
            </div>
          )}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-3">
          <Link
            href="/dashboard"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Отмена
          </Link>
          <button
            type="submit"
            disabled={saving || !title.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Создание..." : "Создать курс"}
          </button>
        </div>
      </form>

      {showAIModal && (
        <AIOutlineModal
          token={token}
          onApply={handleApplyOutline}
          onClose={() => setShowAIModal(false)}
        />
      )}
    </div>
  );
}
