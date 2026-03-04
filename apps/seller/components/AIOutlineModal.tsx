"use client";

import { useState } from "react";
import { ai, type OutlineModule } from "@/lib/api";

interface AIOutlineModalProps {
  token: string;
  onApply: (modules: OutlineModule[]) => void;
  onClose: () => void;
}

export function AIOutlineModal({ token, onApply, onClose }: AIOutlineModalProps) {
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState<string>("beginner");
  const [targetAudience, setTargetAudience] = useState("");
  const [numModules, setNumModules] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<OutlineModule[] | null>(null);

  const handleGenerate = async () => {
    if (!topic.trim() || !targetAudience.trim()) return;
    setError("");
    setLoading(true);
    try {
      const res = await ai.generateCourseOutline(token, {
        topic: topic.trim(),
        level,
        target_audience: targetAudience.trim(),
        num_modules: numModules,
      });
      setResult(res.modules);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка генерации");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold">Сгенерировать структуру курса с помощью AI</h2>
        <p className="mt-1 text-xs text-gray-500">Это действие использует 1 AI-кредит</p>

        {!result ? (
          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Тема курса</label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Например: Основы Python для анализа данных"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Уровень</label>
              <select
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="beginner">Начинающий</option>
                <option value="intermediate">Средний</option>
                <option value="advanced">Продвинутый</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Целевая аудитория</label>
              <input
                type="text"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                placeholder="Например: Студенты без опыта программирования"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">
                Количество модулей: {numModules}
              </label>
              <input
                type="range"
                min={2}
                max={10}
                value={numModules}
                onChange={(e) => setNumModules(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400">
                <span>2</span>
                <span>10</span>
              </div>
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <div className="flex justify-end gap-3">
              <button
                onClick={onClose}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                onClick={handleGenerate}
                disabled={loading || !topic.trim() || !targetAudience.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Генерация...
                  </span>
                ) : (
                  "Сгенерировать"
                )}
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-4">
            <div className="space-y-4">
              {result.map((mod, mi) => (
                <div key={mi} className="rounded-lg border border-gray-200 p-4">
                  <h3 className="font-semibold">
                    Модуль {mi + 1}: {mod.title}
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">{mod.description}</p>
                  <ul className="mt-2 space-y-1">
                    {mod.lessons.map((lesson, li) => (
                      <li key={li} className="flex items-start gap-2 text-sm">
                        <span className="mt-0.5 text-gray-400">{li + 1}.</span>
                        <div>
                          <span className="font-medium">{lesson.title}</span>
                          <span className="ml-2 text-xs text-gray-400">
                            ~{lesson.estimated_duration_minutes} мин
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setResult(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Назад
              </button>
              <button
                onClick={onClose}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                onClick={() => onApply(result)}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
              >
                Применить
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
