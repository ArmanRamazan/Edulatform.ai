"use client";

import { useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useCourseGraph, useCreateConcept, useDeleteConcept } from "@/hooks/use-concepts";

export default function ConceptsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: courseId } = use(params);
  const { token, user } = useAuth();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const { data: graphData } = useCourseGraph(token, courseId);
  const createConcept = useCreateConcept(token, courseId);
  const deleteConcept = useDeleteConcept(token, courseId);

  const isTeacher = user?.role === "teacher";
  const concepts = graphData?.concepts ?? [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
        <nav className="mb-4 text-sm text-gray-500">
          <Link href="/" className="hover:underline">Курсы</Link>
          {" / "}
          <Link href={`/courses/${courseId}`} className="hover:underline">Курс</Link>
          {" / "}
          <span className="text-gray-700">Концепты</span>
        </nav>

        <h1 className="mb-6 text-xl font-bold">Концепты курса</h1>

        {/* Add form (teachers only) */}
        {isTeacher && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!name.trim()) return;
              createConcept.mutate({ name: name.trim(), description: description.trim() }, {
                onSuccess: () => { setName(""); setDescription(""); },
              });
            }}
            className="mb-6 rounded-lg border border-gray-200 bg-white p-4"
          >
            <h2 className="mb-3 text-sm font-semibold text-gray-700">Добавить концепт</h2>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Название концепта"
              className="mb-2 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Описание (опционально)"
              className="mb-3 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!name.trim() || createConcept.isPending}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createConcept.isPending ? "Создаём..." : "Добавить"}
            </button>
          </form>
        )}

        {/* Concepts list */}
        {concepts.length === 0 ? (
          <p className="text-sm text-gray-400">Концепты ещё не добавлены.</p>
        ) : (
          <div className="space-y-2">
            {concepts.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-gray-800">{c.name}</p>
                  {c.description && (
                    <p className="text-xs text-gray-500">{c.description}</p>
                  )}
                  {c.prerequisites.length > 0 && (
                    <p className="text-xs text-gray-400">
                      Требуется: {c.prerequisites.length} концепт(ов)
                    </p>
                  )}
                </div>
                {isTeacher && (
                  <button
                    onClick={() => deleteConcept.mutate(c.id)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Удалить
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
  );
}
