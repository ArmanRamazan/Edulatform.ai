"use client";

import { useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/use-auth";
import { useStartPretest, useAnswerPretest, usePretestResults } from "@/hooks/use-pretest";
import { getErrorMessage } from "@/lib/errors";
import type { PretestStartResponse, AnswerNextResponse, PretestResultsResponse, ConceptResult } from "@/lib/api";

type Step = "idle" | "loading" | "question" | "answering" | "completed";

function MasteryIcon({ mastery, tested }: { mastery: number; tested: boolean }) {
  if (!tested) {
    return <span className="text-lg text-gray-400">—</span>;
  }
  if (mastery >= 0.5) {
    return <span className="text-lg text-green-500">&#10003;</span>;
  }
  return <span className="text-lg text-red-500">&#10007;</span>;
}

function MasteryBadge({ mastery, tested }: { mastery: number; tested: boolean }) {
  if (!tested) return <span className="text-xs text-gray-400">Не проверено</span>;
  if (mastery >= 0.5) return <span className="text-xs text-green-600">Знаете</span>;
  return <span className="text-xs text-red-600">Нужно изучить</span>;
}

function ReadinessRing({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value * circumference);
  const color = pct >= 70 ? "text-green-500" : pct >= 40 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="10" />
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={`${color} transition-all duration-700`}
          transform="rotate(-90 64 64)"
        />
      </svg>
      <span className={`absolute text-2xl font-bold ${color}`}>{pct}%</span>
    </div>
  );
}

function ResultsView({ results, courseId }: { results: PretestResultsResponse; courseId: string }) {
  const knownCount = results.concepts.filter((c) => c.tested && c.mastery >= 0.5).length;
  const totalCount = results.concepts.length;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Результаты вступительного теста</h1>

      <div className="flex flex-col items-center gap-3 rounded-lg border border-gray-200 bg-white p-6">
        <ReadinessRing value={results.overall_readiness} />
        <p className="text-lg font-medium text-gray-700">Общая готовность</p>
        <p className="text-sm text-gray-500">
          Вы уже знаете {knownCount} из {totalCount} концепций
        </p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold">Карта знаний</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {results.concepts.map((c) => (
            <div
              key={c.concept_id}
              className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3"
            >
              <MasteryIcon mastery={c.mastery} tested={c.tested} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-gray-800">{c.name}</p>
                <MasteryBadge mastery={c.mastery} tested={c.tested} />
              </div>
              {c.tested && (
                <span className="text-xs text-gray-400">{Math.round(c.mastery * 100)}%</span>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <Link
          href={`/courses/${courseId}`}
          className="rounded bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          Начать обучение
        </Link>
      </div>
    </div>
  );
}

export default function PretestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: courseId } = use(params);
  const router = useRouter();
  const { token, user, loading: authLoading } = useAuth();

  const startPretest = useStartPretest(token);
  const answerPretest = useAnswerPretest(token);
  const { data: existingResults, isLoading: resultsLoading } = usePretestResults(token, courseId);

  const [step, setStep] = useState<Step>("idle");
  const [pretestId, setPretestId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [conceptName, setConceptName] = useState("");
  const [answerId, setAnswerId] = useState<string | null>(null);
  const [totalConcepts, setTotalConcepts] = useState(0);
  const [progress, setProgress] = useState(0);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [userAnswer, setUserAnswer] = useState("");
  const [results, setResults] = useState<PretestResultsResponse | null>(null);
  const [error, setError] = useState("");

  function applyQuestion(q: string, cId: string, aId: string) {
    setQuestion(q);
    setAnswerId(aId);
    setUserAnswer("");
    setStep("question");
  }

  async function handleStart() {
    setError("");
    setStep("loading");
    try {
      const data = await startPretest.mutateAsync(courseId);
      setPretestId(data.pretest_id);
      setTotalConcepts(data.total_concepts);
      setAnsweredCount(0);
      setProgress(0);
      applyQuestion(data.question, data.concept_id, data.answer_id);
    } catch (e) {
      setError(getErrorMessage(e, "Не удалось запустить тест"));
      setStep("idle");
    }
  }

  async function handleAnswer(answer: string) {
    if (!pretestId || !answerId) return;
    setStep("answering");
    setError("");
    try {
      const data = await answerPretest.mutateAsync({
        pretestId,
        answerId,
        answer,
      });
      setAnsweredCount((c) => c + 1);
      setProgress(data.progress);

      if (data.completed && data.results) {
        setResults(data.results);
        setStep("completed");
      } else if (data.next_question && data.answer_id) {
        applyQuestion(data.next_question, data.concept_id!, data.answer_id);
      }
    } catch (e) {
      setError(getErrorMessage(e, "Ошибка при ответе"));
      setStep("question");
    }
  }

  const isTrueFalse = question.startsWith("True or False:");

  if (authLoading || resultsLoading) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-2xl px-4 py-6">
          <p className="text-gray-400">Загрузка...</p>
        </main>
      </>
    );
  }

  if (!user || !token) {
    router.replace("/login");
    return null;
  }

  if (existingResults && step !== "completed" && !results) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-2xl px-4 py-6">
          <Link href={`/courses/${courseId}`} className="mb-4 inline-block text-sm text-blue-600 hover:underline">
            &larr; Назад к курсу
          </Link>
          <ResultsView results={existingResults} courseId={courseId} />
        </main>
      </>
    );
  }

  if (step === "completed" && results) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-2xl px-4 py-6">
          <Link href={`/courses/${courseId}`} className="mb-4 inline-block text-sm text-blue-600 hover:underline">
            &larr; Назад к курсу
          </Link>
          <ResultsView results={results} courseId={courseId} />
        </main>
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-2xl px-4 py-6">
        <Link href={`/courses/${courseId}`} className="mb-4 inline-block text-sm text-blue-600 hover:underline">
          &larr; Назад к курсу
        </Link>

        {step === "idle" && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
            <h1 className="mb-3 text-2xl font-bold">Вступительный тест</h1>
            <p className="mb-6 text-gray-600">
              Ответьте на несколько вопросов, чтобы мы определили ваш уровень знаний
              и подготовили персональный план обучения.
            </p>
            {error && (
              <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">{error}</div>
            )}
            <button
              onClick={handleStart}
              className="rounded bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              Начать тест
            </button>
          </div>
        )}

        {step === "loading" && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
            <p className="text-gray-500">Подготовка вопроса...</p>
          </div>
        )}

        {(step === "question" || step === "answering") && (
          <div className="space-y-4">
            {/* Progress */}
            <div>
              <div className="mb-1 flex justify-between text-sm text-gray-500">
                <span>Вопрос {answeredCount + 1}{totalConcepts > 0 ? ` из ~${totalConcepts}` : ""}</span>
                <span>{Math.round(progress * 100)}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-gray-200">
                <div
                  className="h-2 rounded-full bg-blue-600 transition-all"
                  style={{ width: `${Math.round(progress * 100)}%` }}
                />
              </div>
            </div>

            {/* Question card */}
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <p className="mb-6 text-lg font-medium text-gray-800">{question}</p>

              {error && (
                <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">{error}</div>
              )}

              {isTrueFalse ? (
                <div className="flex gap-3">
                  <button
                    onClick={() => handleAnswer("True")}
                    disabled={step === "answering"}
                    className="flex-1 rounded border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-700 hover:bg-green-100 disabled:opacity-50"
                  >
                    True
                  </button>
                  <button
                    onClick={() => handleAnswer("False")}
                    disabled={step === "answering"}
                    className="flex-1 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
                  >
                    False
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <input
                    type="text"
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && userAnswer.trim()) handleAnswer(userAnswer.trim());
                    }}
                    placeholder="Введите ответ..."
                    className="w-full rounded border border-gray-200 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none"
                    disabled={step === "answering"}
                  />
                  <button
                    onClick={() => handleAnswer(userAnswer.trim())}
                    disabled={step === "answering" || !userAnswer.trim()}
                    className="rounded bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {step === "answering" ? "Отправка..." : "Ответить"}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </>
  );
}
