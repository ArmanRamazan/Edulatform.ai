"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import {
  courses,
  modules as modulesApi,
  lessons as lessonsApi,
  type Course,
  type CurriculumModule,
  type Lesson,
} from "@/lib/api";
import { getErrorMessage } from "@/lib/errors";
import { useAuth } from "@/hooks/use-auth";

export default function EditCoursePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, token } = useAuth();
  const [course, setCourse] = useState<Course | null>(null);
  const [curriculum, setCurriculum] = useState<CurriculumModule[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isFree, setIsFree] = useState(true);
  const [price, setPrice] = useState("");
  const [duration, setDuration] = useState("");
  const [level, setLevel] = useState("beginner");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // Module form
  const [newModuleTitle, setNewModuleTitle] = useState("");
  // Lesson form
  const [addingLessonTo, setAddingLessonTo] = useState<string | null>(null);
  const [newLessonTitle, setNewLessonTitle] = useState("");
  const [newLessonContent, setNewLessonContent] = useState("");
  // Lesson editing
  const [editingLesson, setEditingLesson] = useState<string | null>(null);
  const [editLessonTitle, setEditLessonTitle] = useState("");
  const [editLessonContent, setEditLessonContent] = useState("");

  useEffect(() => {
    courses.get(id).then((c) => {
      setCourse(c);
      setTitle(c.title);
      setDescription(c.description);
      setIsFree(c.is_free);
      setPrice(c.price?.toString() ?? "");
      setDuration(c.duration_minutes.toString());
      setLevel(c.level);
    }).catch((e) => setError(e.message));
    loadCurriculum();
  }, [id]);

  function loadCurriculum() {
    courses.curriculum(id).then((r) => setCurriculum(r.modules)).catch(() => {});
  }

  async function handleSave() {
    if (!token) return;
    setSaving(true);
    setMessage("");
    try {
      const updated = await courses.update(token, id, {
        title,
        description,
        is_free: isFree,
        price: isFree ? undefined : parseFloat(price),
        duration_minutes: parseInt(duration) || 0,
        level,
      });
      setCourse(updated);
      setMessage("Сохранено");
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function handleAddModule() {
    if (!token || !newModuleTitle.trim()) return;
    try {
      await modulesApi.create(token, id, {
        title: newModuleTitle.trim(),
        order: curriculum.length,
      });
      setNewModuleTitle("");
      loadCurriculum();
    } catch (e) {
      setError(getErrorMessage(e));
    }
  }

  async function handleDeleteModule(moduleId: string) {
    if (!token || !confirm("Удалить модуль и все его уроки?")) return;
    try {
      await modulesApi.delete(token, moduleId);
      loadCurriculum();
    } catch (e) {
      setError(getErrorMessage(e));
    }
  }

  async function handleAddLesson(moduleId: string) {
    if (!token || !newLessonTitle.trim()) return;
    try {
      const mod = curriculum.find((m) => m.id === moduleId);
      await lessonsApi.create(token, moduleId, {
        title: newLessonTitle.trim(),
        content: newLessonContent,
        order: mod?.lessons.length ?? 0,
      });
      setNewLessonTitle("");
      setNewLessonContent("");
      setAddingLessonTo(null);
      loadCurriculum();
    } catch (e) {
      setError(getErrorMessage(e));
    }
  }

  async function handleDeleteLesson(lessonId: string) {
    if (!token || !confirm("Удалить урок?")) return;
    try {
      await lessonsApi.delete(token, lessonId);
      loadCurriculum();
    } catch (e) {
      setError(getErrorMessage(e));
    }
  }

  function startEditLesson(lesson: Lesson) {
    setEditingLesson(lesson.id);
    setEditLessonTitle(lesson.title);
    setEditLessonContent(lesson.content || "");
  }

  async function handleSaveLesson(lessonId: string) {
    if (!token) return;
    try {
      await lessonsApi.update(token, lessonId, {
        title: editLessonTitle,
        content: editLessonContent,
      });
      setEditingLesson(null);
      loadCurriculum();
    } catch (e) {
      setError(getErrorMessage(e));
    }
  }

  if (!user || user.role !== "teacher") {
    return (
      <main className="mx-auto max-w-3xl px-4 py-6">
        <p className="text-gray-500">Доступ только для преподавателей</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
        <div className="mb-4 flex gap-4">
          <Link href="/my-courses" className="text-sm text-blue-600 hover:underline">
            &larr; Мои курсы
          </Link>
          <Link href={`/courses/${id}`} className="text-sm text-blue-600 hover:underline">
            Страница курса
          </Link>
        </div>

        {error && <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        {message && <div className="mb-4 rounded bg-green-50 p-3 text-sm text-green-600">{message}</div>}

        {!course ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : (
          <>
            {/* Course info form */}
            <section className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-4 text-lg font-bold">Информация о курсе</h2>
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Название</label>
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full rounded border border-gray-200 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Описание</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full rounded border border-gray-200 px-3 py-2 text-sm"
                    rows={3}
                  />
                </div>
                <div className="flex gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Уровень</label>
                    <select
                      value={level}
                      onChange={(e) => setLevel(e.target.value)}
                      className="rounded border border-gray-200 px-3 py-2 text-sm"
                    >
                      <option value="beginner">Начальный</option>
                      <option value="intermediate">Средний</option>
                      <option value="advanced">Продвинутый</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Длительность (мин)</label>
                    <input
                      type="number"
                      value={duration}
                      onChange={(e) => setDuration(e.target.value)}
                      className="w-28 rounded border border-gray-200 px-3 py-2 text-sm"
                    />
                  </div>
                </div>
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
                      placeholder="Цена"
                      className="w-28 rounded border border-gray-200 px-3 py-2 text-sm"
                    />
                  )}
                </div>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Сохранение..." : "Сохранить"}
                </button>
              </div>
            </section>

            {/* Modules & Lessons */}
            <section className="rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-4 text-lg font-bold">Модули и уроки</h2>

              {curriculum.map((mod) => (
                <div key={mod.id} className="mb-4 rounded border border-gray-100 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="font-semibold">{mod.title}</h3>
                    <button
                      onClick={() => handleDeleteModule(mod.id)}
                      className="text-xs text-red-500 hover:underline"
                    >
                      Удалить модуль
                    </button>
                  </div>
                  <ul className="mb-2 space-y-1">
                    {mod.lessons.map((l) => (
                      <li key={l.id}>
                        {editingLesson === l.id ? (
                          <div className="space-y-2 rounded border border-blue-100 bg-blue-50 p-2">
                            <input
                              value={editLessonTitle}
                              onChange={(e) => setEditLessonTitle(e.target.value)}
                              className="w-full rounded border border-gray-200 px-2 py-1 text-sm"
                            />
                            <textarea
                              value={editLessonContent}
                              onChange={(e) => setEditLessonContent(e.target.value)}
                              className="w-full rounded border border-gray-200 px-2 py-1 text-sm"
                              rows={3}
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleSaveLesson(l.id)}
                                className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
                              >
                                Сохранить
                              </button>
                              <button
                                onClick={() => setEditingLesson(null)}
                                className="text-xs text-gray-500 hover:underline"
                              >
                                Отмена
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-700">{l.title}</span>
                            <div className="flex gap-2">
                              <button
                                onClick={() => startEditLesson(l)}
                                className="text-xs text-blue-500 hover:underline"
                              >
                                Редактировать
                              </button>
                              <button
                                onClick={() => handleDeleteLesson(l.id)}
                                className="text-xs text-red-400 hover:underline"
                              >
                                Удалить
                              </button>
                            </div>
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                  {addingLessonTo === mod.id ? (
                    <div className="space-y-2 border-t border-gray-100 pt-2">
                      <input
                        value={newLessonTitle}
                        onChange={(e) => setNewLessonTitle(e.target.value)}
                        placeholder="Название урока"
                        className="w-full rounded border border-gray-200 px-2 py-1 text-sm"
                      />
                      <textarea
                        value={newLessonContent}
                        onChange={(e) => setNewLessonContent(e.target.value)}
                        placeholder="Содержимое урока"
                        className="w-full rounded border border-gray-200 px-2 py-1 text-sm"
                        rows={2}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleAddLesson(mod.id)}
                          className="rounded bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700"
                        >
                          Добавить
                        </button>
                        <button
                          onClick={() => setAddingLessonTo(null)}
                          className="text-xs text-gray-500 hover:underline"
                        >
                          Отмена
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setAddingLessonTo(mod.id)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      + Добавить урок
                    </button>
                  )}
                </div>
              ))}

              <div className="flex gap-2 border-t border-gray-100 pt-3">
                <input
                  value={newModuleTitle}
                  onChange={(e) => setNewModuleTitle(e.target.value)}
                  placeholder="Название нового модуля"
                  className="flex-1 rounded border border-gray-200 px-3 py-2 text-sm"
                />
                <button
                  onClick={handleAddModule}
                  className="rounded bg-green-600 px-3 py-2 text-sm text-white hover:bg-green-700"
                >
                  + Модуль
                </button>
              </div>
            </section>
          </>
        )}
      </main>
  );
}
