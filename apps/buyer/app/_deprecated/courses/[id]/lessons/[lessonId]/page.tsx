"use client";

import { useState, use } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { lessons as lessonsApi } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { useCurriculum } from "@/hooks/use-courses";
import { useCompletedLessons, useCompleteLesson } from "@/hooks/use-progress";
import { useQuiz, useSubmitQuiz, useCreateQuiz } from "@/hooks/use-quiz";
import { useSummary, useGenerateQuiz } from "@/hooks/use-ai";
import { usePaywall } from "@/hooks/use-paywall";
import { getErrorMessage } from "@/lib/errors";
import type { QuizQuestionResult } from "@/lib/api";

const PaywallDialog = dynamic(
  () => import("@/components/PaywallDialog").then((m) => ({ default: m.PaywallDialog })),
  { ssr: false },
);

const TutorDrawer = dynamic(
  () => import("@/components/TutorDrawer").then((m) => ({ default: m.TutorDrawer })),
  { ssr: false },
);

export default function LessonPage({
  params,
}: {
  params: Promise<{ id: string; lessonId: string }>;
}) {
  const { id: courseId, lessonId } = use(params);
  const { token, user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { data: lesson, error } = useQuery({
    queryKey: ["lessons", lessonId],
    queryFn: () => lessonsApi.get(lessonId),
  });

  const { data: curriculumData } = useCurriculum(courseId);
  const curriculum = curriculumData?.modules ?? [];
  const courseTitle = curriculumData?.course.title ?? "...";

  const { data: completedData } = useCompletedLessons(token, courseId);
  const completedIds = new Set(completedData?.completed_lesson_ids ?? []);
  const completed = completedIds.has(lessonId);

  const completeLesson = useCompleteLesson(token, courseId);

  const { data: quizData } = useQuiz(token, lessonId);

  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [quizResults, setQuizResults] = useState<QuizQuestionResult[] | null>(null);
  const [quizScore, setQuizScore] = useState<number | null>(null);
  const [tutorOpen, setTutorOpen] = useState(false);
  const [paywallFeature, setPaywallFeature] = useState<string | undefined>();

  const { showPaywall, paywallOpen, openPaywall, closePaywall, creditStatus } =
    usePaywall(token);

  const { data: summaryData, isLoading: summaryLoading } = useSummary(
    showPaywall ? null : token, lessonId, lesson?.content ?? ""
  );

  const submitQuiz = useSubmitQuiz(token, quizData?.id ?? "");
  const generateQuiz = useGenerateQuiz(token);
  const createQuiz = useCreateQuiz(token, lessonId);

  const isTeacher = !!user && !!curriculumData && user.id === curriculumData.course.teacher_id;

  const handleGenerateQuiz = () => {
    if (!lesson) return;
    if (showPaywall) {
      setPaywallFeature("Генерация квиза");
      openPaywall();
      return;
    }
    generateQuiz.mutate(
      { lessonId, content: lesson.content },
      {
        onSuccess: (data) => {
          createQuiz.mutate({
            lesson_id: lessonId,
            course_id: courseId,
            questions: data.questions,
          });
        },
      }
    );
  };

  const isGenerating = generateQuiz.isPending || createQuiz.isPending;

  const allLessons = curriculum.flatMap((m) => m.lessons);
  const currentIdx = allLessons.findIndex((l) => l.id === lessonId);
  const prevLesson = currentIdx > 0 ? allLessons[currentIdx - 1] : null;
  const nextLesson = currentIdx < allLessons.length - 1 ? allLessons[currentIdx + 1] : null;

  return (
    <>
      <div className="mx-auto max-w-5xl px-4 py-6">
        {/* Breadcrumbs */}
        <nav className="mb-4 text-sm text-gray-500">
          <Link href="/" className="hover:underline">Курсы</Link>
          {" / "}
          <Link href={`/courses/${courseId}`} className="hover:underline">
            {courseTitle}
          </Link>
          {lesson && (
            <>
              {" / "}
              <span className="text-gray-700">{lesson.title}</span>
            </>
          )}
        </nav>

        {/* Mobile toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="mb-3 rounded border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 md:hidden"
        >
          {sidebarOpen ? "Скрыть программу" : "Показать программу"}
        </button>

        <div className="flex gap-6">
        {/* Sidebar */}
        <aside className={`${sidebarOpen ? "block" : "hidden"} w-64 shrink-0 md:block`}>
          <Link href={`/courses/${courseId}`} className="mb-3 block text-sm text-blue-600 hover:underline">
            &larr; К курсу
          </Link>
          <nav className="space-y-3">
            {curriculum.map((mod) => (
              <div key={mod.id}>
                <h4 className="mb-1 text-xs font-semibold uppercase text-gray-400">{mod.title}</h4>
                <ul className="space-y-1">
                  {mod.lessons.map((l) => (
                    <li key={l.id}>
                      <Link
                        href={`/courses/${courseId}/lessons/${l.id}`}
                        className={`flex items-center gap-1.5 rounded px-2 py-1 text-sm ${
                          l.id === lessonId
                            ? "bg-blue-50 font-medium text-blue-700"
                            : "text-gray-600 hover:bg-gray-50"
                        }`}
                      >
                        {completedIds.has(l.id) ? (
                          <span className="text-green-500">&#10003;</span>
                        ) : (
                          <span className="text-gray-300">&#9675;</span>
                        )}
                        <span className="truncate">{l.title}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </aside>

        {/* Main content */}
        <main className="min-w-0 flex-1">
          {error ? (
            <div className="rounded bg-red-50 p-4 text-red-600">
              {getErrorMessage(error)}
            </div>
          ) : !lesson ? (
            <p className="text-gray-400">Загрузка...</p>
          ) : (
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <h1 className="mb-4 text-xl font-bold">{lesson.title}</h1>

              {lesson.video_url && (
                <div className="mb-4 aspect-video">
                  <iframe
                    src={lesson.video_url}
                    className="h-full w-full rounded"
                    allowFullScreen
                    loading="lazy"
                    title="Видео урока"
                  />
                </div>
              )}

              <div className="prose prose-sm mb-6 max-w-none whitespace-pre-wrap text-gray-700">
                {lesson.content}
              </div>

              {/* Summary */}
              {summaryLoading && token && (
                <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 p-4">
                  <h3 className="mb-2 text-sm font-semibold text-blue-700">Краткое содержание</h3>
                  <p className="text-sm text-blue-600">Генерируем...</p>
                </div>
              )}
              {summaryData && (
                <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 p-4">
                  <h3 className="mb-2 text-sm font-semibold text-blue-700">Краткое содержание</h3>
                  <p className="whitespace-pre-wrap text-sm text-gray-700">{summaryData.summary}</p>
                </div>
              )}
              {!summaryData && !summaryLoading && token && showPaywall && (
                <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <h3 className="mb-2 text-sm font-semibold text-gray-500">Краткое содержание</h3>
                  <p className="text-sm text-gray-500">
                    AI-кредиты исчерпаны.{" "}
                    <button
                      onClick={() => {
                        setPaywallFeature("Генерация краткого содержания");
                        openPaywall();
                      }}
                      className="text-blue-600 hover:underline"
                    >
                      Улучшить тариф
                    </button>
                  </p>
                </div>
              )}

              {/* Generate Quiz (teacher only) */}
              {!quizData && isTeacher && (
                <div className="mb-4 flex items-center gap-2 rounded-lg border border-purple-100 bg-purple-50 p-3">
                  <span className="text-sm text-purple-700">Для этого урока ещё нет квиза.</span>
                  <button
                    onClick={handleGenerateQuiz}
                    disabled={isGenerating}
                    className="rounded bg-purple-600 px-3 py-1.5 text-sm text-white hover:bg-purple-700 disabled:opacity-50"
                  >
                    {isGenerating ? "Генерируем квиз..." : "Сгенерировать квиз"}
                  </button>
                  {(generateQuiz.isError || createQuiz.isError) && (
                    <span className="text-sm text-red-600">
                      {getErrorMessage(generateQuiz.error || createQuiz.error)}
                    </span>
                  )}
                </div>
              )}

              {/* Quiz */}
              {quizData && (
                <div className="mb-4 rounded-lg border border-purple-100 bg-purple-50 p-4">
                  <h3 className="mb-3 text-sm font-semibold text-purple-700">
                    Проверьте себя ({quizData.questions.length} вопросов)
                  </h3>
                  <div className="space-y-4">
                    {quizData.questions.map((q, qi) => (
                      <div key={q.id}>
                        <p className="mb-2 text-sm font-medium text-gray-800">{qi + 1}. {q.text}</p>
                        <div className="space-y-1">
                          {q.options.map((opt, oi) => {
                            const result = quizResults?.find(r => r.question_id === q.id);
                            let optClass = "border-gray-200 hover:bg-gray-50";
                            if (result) {
                              if (oi === result.correct_index) optClass = "border-green-300 bg-green-50";
                              else if (oi === result.selected && !result.is_correct) optClass = "border-red-300 bg-red-50";
                            } else if (selectedAnswers[qi] === oi) {
                              optClass = "border-purple-300 bg-purple-100";
                            }
                            return (
                              <button
                                key={oi}
                                onClick={() => {
                                  if (!quizResults) setSelectedAnswers(prev => ({ ...prev, [qi]: oi }));
                                }}
                                disabled={!!quizResults}
                                className={`block w-full rounded border px-3 py-1.5 text-left text-sm ${optClass} disabled:cursor-default`}
                              >
                                {opt}
                              </button>
                            );
                          })}
                        </div>
                        {quizResults?.find(r => r.question_id === q.id)?.explanation && (
                          <p className="mt-1 text-xs text-gray-500">
                            {quizResults.find(r => r.question_id === q.id)!.explanation}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>

                  {quizScore !== null ? (
                    <div className="mt-4 rounded bg-white p-3 text-center">
                      <p className="text-lg font-bold text-purple-700">
                        {Math.round(quizScore * 100)}%
                      </p>
                      <p className="text-sm text-gray-500">
                        Правильных: {quizResults?.filter(r => r.is_correct).length} из {quizData.questions.length}
                      </p>
                      <button
                        onClick={() => {
                          setQuizResults(null);
                          setQuizScore(null);
                          setSelectedAnswers({});
                        }}
                        className="mt-2 text-sm text-purple-600 hover:underline"
                      >
                        Попробовать ещё раз
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        const answers = quizData.questions.map((_, i) => selectedAnswers[i] ?? 0);
                        submitQuiz.mutate(answers, {
                          onSuccess: (data) => {
                            setQuizResults(data.results);
                            setQuizScore(data.score);
                          },
                        });
                      }}
                      disabled={submitQuiz.isPending || Object.keys(selectedAnswers).length < quizData.questions.length}
                      className="mt-4 rounded bg-purple-600 px-4 py-2 text-sm text-white hover:bg-purple-700 disabled:opacity-50"
                    >
                      {submitQuiz.isPending ? "Проверяем..." : "Проверить ответы"}
                    </button>
                  )}
                </div>
              )}

              {/* Tutor button */}
              {token && (
                <div className="mb-4 flex items-center gap-2 rounded-lg border border-teal-100 bg-teal-50 p-3">
                  <span className="text-sm text-teal-700">Не понимаете материал?</span>
                  <button
                    onClick={() => {
                      if (showPaywall) {
                        setPaywallFeature("Чат с AI-тьютором");
                        openPaywall();
                      } else {
                        setTutorOpen(true);
                      }
                    }}
                    className="rounded bg-teal-600 px-3 py-1.5 text-sm text-white hover:bg-teal-700"
                  >
                    Спросить AI-тьютора
                  </button>
                </div>
              )}

              <div className="flex items-center gap-3 border-t border-gray-100 pt-4">
                {completed ? (
                  <span className="rounded bg-green-100 px-3 py-1.5 text-sm text-green-700">
                    &#10003; Урок завершён
                  </span>
                ) : token ? (
                  <button
                    onClick={() => completeLesson.mutate(lessonId)}
                    disabled={completeLesson.isPending}
                    className="rounded bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    {completeLesson.isPending ? "Завершаем..." : "Завершить урок"}
                  </button>
                ) : null}

                <div className="ml-auto flex gap-2">
                  {prevLesson && (
                    <Link
                      href={`/courses/${courseId}/lessons/${prevLesson.id}`}
                      className="rounded border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
                    >
                      &larr; Назад
                    </Link>
                  )}
                  {nextLesson ? (
                    <Link
                      href={`/courses/${courseId}/lessons/${nextLesson.id}`}
                      className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
                    >
                      Далее &rarr;
                    </Link>
                  ) : completed ? (
                    <Link
                      href={`/courses/${courseId}`}
                      className="rounded bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700"
                    >
                      Курс завершён
                    </Link>
                  ) : null}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
      </div>

      {token && lesson && (
        <TutorDrawer
          open={tutorOpen}
          onClose={() => setTutorOpen(false)}
          token={token}
          lessonId={lessonId}
          lessonContent={lesson.content}
        />
      )}

      <PaywallDialog
        open={paywallOpen}
        onClose={closePaywall}
        feature={paywallFeature}
        limit={creditStatus?.limit}
        resetAt={creditStatus?.reset_at}
      />
    </>
  );
}
