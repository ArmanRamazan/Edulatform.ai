"use client";

import { useState } from "react";
import { ai } from "@/lib/api";

interface AILessonModalProps {
  token: string;
  lessonTitle: string;
  courseContext?: string;
  onApply: (content: string, durationMinutes: number) => void;
  onClose: () => void;
}

export function AILessonModal({ token, lessonTitle, courseContext, onApply, onClose }: AILessonModalProps) {
  const [format, setFormat] = useState<string>("article");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ content: string; estimated_duration_minutes: number } | null>(null);

  const handleGenerate = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await ai.generateLessonContent(token, {
        title: lessonTitle,
        course_context: courseContext,
        format,
      });
      setResult({ content: res.content, estimated_duration_minutes: res.estimated_duration_minutes });
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
        <h2 className="text-lg font-bold">Сгенерировать контент для урока</h2>
        <p className="mt-1 text-sm text-gray-600">&laquo;{lessonTitle}&raquo;</p>
        <p className="mt-1 text-xs text-gray-500">Это действие использует 1 AI-кредит</p>

        {!result ? (
          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Формат</label>
              <div className="flex gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="format"
                    value="article"
                    checked={format === "article"}
                    onChange={() => setFormat("article")}
                  />
                  Статья
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="format"
                    value="tutorial"
                    checked={format === "tutorial"}
                    onChange={() => setFormat("tutorial")}
                  />
                  Пошаговый туториал
                </label>
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
                disabled={loading}
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
            <div className="max-h-96 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-4">
              <pre className="whitespace-pre-wrap text-sm">{result.content}</pre>
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Примерная длительность: {result.estimated_duration_minutes} мин
            </p>

            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

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
                onClick={() => onApply(result.content, result.estimated_duration_minutes)}
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
