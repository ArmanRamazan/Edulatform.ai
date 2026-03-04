"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useCurriculum, useUpdateCourse } from "@/hooks/use-courses";
import {
  modules as modulesApi,
  lessons as lessonsApi,
  type Lesson,
  type CurriculumModule,
} from "@/lib/api";
import { AIOutlineModal } from "@/components/AIOutlineModal";
import { AILessonModal } from "@/components/AILessonModal";
import type { OutlineModule } from "@/lib/api";

export default function EditCoursePage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.id as string;
  const { token, loading: authLoading } = useAuth();
  const { data: curriculum, isLoading, refetch } = useCurriculum(token, courseId);
  const updateCourse = useUpdateCourse(token);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [initialized, setInitialized] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [showAIOutline, setShowAIOutline] = useState(false);
  const [aiLessonTarget, setAiLessonTarget] = useState<Lesson | null>(null);
  const [expandedLesson, setExpandedLesson] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState<Record<string, string>>({});

  if (curriculum && !initialized) {
    setTitle(curriculum.course.title);
    setDescription(curriculum.course.description);
    setInitialized(true);
  }

  if (authLoading || isLoading) {
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

  if (!curriculum) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-center">
        <p className="text-gray-500">Курс не найден</p>
        <Link href="/dashboard" className="mt-2 inline-block text-sm text-blue-600">
          Назад к курсам
        </Link>
      </div>
    );
  }

  const handleSaveCourse = async () => {
    setSaving(true);
    setError("");
    try {
      await updateCourse.mutateAsync({
        id: courseId,
        body: { title: title.trim(), description: description.trim() },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  const handleAddModule = async () => {
    const name = prompt("Название модуля:");
    if (!name?.trim()) return;
    try {
      await modulesApi.create(token, courseId, {
        title: name.trim(),
        order: curriculum.modules.length,
      });
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const handleDeleteModule = async (moduleId: string) => {
    if (!confirm("Удалить модуль и все его уроки?")) return;
    try {
      await modulesApi.delete(token, moduleId);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const handleAddLesson = async (moduleId: string) => {
    const name = prompt("Название урока:");
    if (!name?.trim()) return;
    try {
      const mod = curriculum.modules.find((m) => m.id === moduleId);
      await lessonsApi.create(token, moduleId, {
        title: name.trim(),
        content: "",
        video_url: null,
        duration_minutes: 0,
        order: mod?.lessons.length ?? 0,
      });
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const handleDeleteLesson = async (lessonId: string) => {
    if (!confirm("Удалить урок?")) return;
    try {
      await lessonsApi.delete(token, lessonId);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const handleSaveLessonContent = async (lessonId: string) => {
    const content = editingContent[lessonId];
    if (content === undefined) return;
    try {
      await lessonsApi.update(token, lessonId, { content });
      setEditingContent((prev) => {
        const next = { ...prev };
        delete next[lessonId];
        return next;
      });
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const handleApplyAIContent = (content: string, durationMinutes: number) => {
    if (!aiLessonTarget) return;
    const lessonId = aiLessonTarget.id;

    if (aiLessonTarget.content && !confirm("Заменить текущий контент урока сгенерированным?")) {
      setAiLessonTarget(null);
      return;
    }

    setEditingContent((prev) => ({ ...prev, [lessonId]: content }));
    setExpandedLesson(lessonId);
    setAiLessonTarget(null);

    lessonsApi.update(token, lessonId, { content, duration_minutes: durationMinutes }).then(() => {
      setEditingContent((prev) => {
        const next = { ...prev };
        delete next[lessonId];
        return next;
      });
      refetch();
    });
  };

  const handleApplyOutline = async (modules: OutlineModule[]) => {
    if (
      curriculum.modules.length > 0 &&
      !confirm("Это добавит новые модули к существующим. Продолжить?")
    ) {
      setShowAIOutline(false);
      return;
    }

    setShowAIOutline(false);
    setError("");

    try {
      for (let mi = 0; mi < modules.length; mi++) {
        const mod = modules[mi];
        const created = await modulesApi.create(token, courseId, {
          title: mod.title,
          order: curriculum.modules.length + mi,
        });

        for (let li = 0; li < mod.lessons.length; li++) {
          const lesson = mod.lessons[li];
          await lessonsApi.create(token, created.id, {
            title: lesson.title,
            content: lesson.description,
            video_url: null,
            duration_minutes: lesson.estimated_duration_minutes,
            order: li,
          });
        }
      }
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка при применении структуры");
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">
          &larr; Назад
        </Link>
        <h1 className="text-2xl font-bold">Редактировать курс</h1>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {error}
          <button onClick={() => setError("")} className="ml-2 font-medium underline">
            Скрыть
          </button>
        </div>
      )}

      <div className="space-y-6">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 font-semibold">Основная информация</h2>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Название</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Описание</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div className="flex justify-end">
              <button
                onClick={handleSaveCourse}
                disabled={saving}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Сохранение..." : "Сохранить"}
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Модули и уроки</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setShowAIOutline(true)}
                className="rounded-lg border border-purple-300 bg-purple-50 px-3 py-1.5 text-sm font-medium text-purple-700 hover:bg-purple-100"
              >
                Сгенерировать структуру с помощью AI
              </button>
              <button
                onClick={handleAddModule}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Добавить модуль
              </button>
            </div>
          </div>

          {curriculum.modules.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center">
              <p className="text-sm text-gray-500">
                Модулей пока нет. Используйте AI или добавьте модуль вручную.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {curriculum.modules.map((mod: CurriculumModule, mi: number) => (
                <div key={mod.id} className="rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold">
                      Модуль {mi + 1}: {mod.title}
                    </h3>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleAddLesson(mod.id)}
                        className="text-xs text-blue-600 hover:text-blue-700"
                      >
                        + Урок
                      </button>
                      <button
                        onClick={() => handleDeleteModule(mod.id)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        Удалить
                      </button>
                    </div>
                  </div>

                  {mod.lessons.length === 0 ? (
                    <p className="mt-2 text-xs text-gray-400">Нет уроков</p>
                  ) : (
                    <ul className="mt-2 space-y-2">
                      {mod.lessons.map((lesson: Lesson, li: number) => (
                        <li key={lesson.id} className="rounded border border-gray-100 bg-gray-50 p-3">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">
                              {li + 1}. {lesson.title}
                            </span>
                            <div className="flex gap-2">
                              <button
                                onClick={() => setAiLessonTarget(lesson)}
                                className="text-xs text-purple-600 hover:text-purple-700"
                              >
                                AI контент
                              </button>
                              <button
                                onClick={() =>
                                  setExpandedLesson(expandedLesson === lesson.id ? null : lesson.id)
                                }
                                className="text-xs text-blue-600 hover:text-blue-700"
                              >
                                {expandedLesson === lesson.id ? "Свернуть" : "Редактировать"}
                              </button>
                              <button
                                onClick={() => handleDeleteLesson(lesson.id)}
                                className="text-xs text-red-500 hover:text-red-700"
                              >
                                Удалить
                              </button>
                            </div>
                          </div>

                          {expandedLesson === lesson.id && (
                            <div className="mt-3">
                              <textarea
                                value={
                                  editingContent[lesson.id] !== undefined
                                    ? editingContent[lesson.id]
                                    : lesson.content
                                }
                                onChange={(e) =>
                                  setEditingContent((prev) => ({
                                    ...prev,
                                    [lesson.id]: e.target.value,
                                  }))
                                }
                                rows={8}
                                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                                placeholder="Содержимое урока (Markdown)"
                              />
                              <div className="mt-2 flex justify-end gap-2">
                                <button
                                  onClick={() => setAiLessonTarget(lesson)}
                                  className="rounded border border-purple-300 bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700 hover:bg-purple-100"
                                >
                                  Сгенерировать контент
                                </button>
                                {editingContent[lesson.id] !== undefined && (
                                  <button
                                    onClick={() => handleSaveLessonContent(lesson.id)}
                                    className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
                                  >
                                    Сохранить
                                  </button>
                                )}
                              </div>
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showAIOutline && (
        <AIOutlineModal
          token={token}
          onApply={handleApplyOutline}
          onClose={() => setShowAIOutline(false)}
        />
      )}

      {aiLessonTarget && (
        <AILessonModal
          token={token}
          lessonTitle={aiLessonTarget.title}
          courseContext={curriculum.course.title}
          onApply={handleApplyAIContent}
          onClose={() => setAiLessonTarget(null)}
        />
      )}
    </div>
  );
}
