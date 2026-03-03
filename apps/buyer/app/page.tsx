"use client";

import { useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { CourseCard } from "@/components/CourseCard";
import { useCourseList, useCategories } from "@/hooks/use-courses";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/errors";

export function HeroSection({ isLoggedIn }: { isLoggedIn: boolean }) {
  return (
    <section className="bg-gradient-to-br from-blue-600 to-indigo-700 px-4 py-20 text-white">
      <div className="mx-auto max-w-4xl text-center">
        <h1 className="mb-4 text-4xl font-extrabold tracking-tight sm:text-5xl">
          Учитесь быстрее с AI-тьютором
        </h1>
        <p className="mx-auto mb-8 max-w-2xl text-lg text-blue-100">
          Курсы, адаптивные тесты, флеш-карточки и Socratic-тьютор в одном месте
        </p>

        <div className="mb-16 flex items-center justify-center gap-4">
          {isLoggedIn ? (
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
          )}
        </div>

        <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
          <div>
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-white/20 text-2xl">
              🎓
            </div>
            <h3 className="mb-1 font-semibold">AI-тьютор</h3>
            <p className="text-sm text-blue-100">
              Задаёт вопросы в сократовском стиле, помогает понять, а не запомнить
            </p>
          </div>
          <div>
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-white/20 text-2xl">
              🔄
            </div>
            <h3 className="mb-1 font-semibold">Адаптивные повторения</h3>
            <p className="text-sm text-blue-100">
              Флеш-карточки с алгоритмом FSRS, повторяйте только то, что забыли
            </p>
          </div>
          <div>
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-white/20 text-2xl">
              🏆
            </div>
            <h3 className="mb-1 font-semibold">Геймификация</h3>
            <p className="text-sm text-blue-100">
              XP, серии активности, значки за достижения
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function SocialProofSection() {
  return (
    <section className="bg-white px-4 py-16">
      <div className="mx-auto max-w-4xl text-center">
        <h2 className="mb-8 text-2xl font-bold text-gray-900">
          Уже учатся тысячи студентов
        </h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-6">
            <p className="text-3xl font-bold text-blue-600">7 сервисов</p>
            <p className="mt-1 text-sm text-gray-500">Микросервисная архитектура</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-6">
            <p className="text-3xl font-bold text-blue-600">AI + FSRS</p>
            <p className="mt-1 text-sm text-gray-500">Умные повторения</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-6">
            <p className="text-3xl font-bold text-blue-600">298 тестов</p>
            <p className="mt-1 text-sm text-gray-500">Надёжная платформа</p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function HomePage() {
  const { user, loading: authLoading } = useAuth();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [level, setLevel] = useState("");
  const [isFree, setIsFree] = useState<string>("");
  const [sortBy, setSortBy] = useState("created_at");

  const { data: categoryList = [] } = useCategories();
  const { data, isLoading, error } = useCourseList({
    q: search || undefined,
    category_id: categoryId || undefined,
    level: level || undefined,
    is_free: isFree === "" ? undefined : isFree === "true",
    sort_by: sortBy,
    limit: 20,
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearch(query);
  }

  const isLoggedIn = !authLoading && !!user;

  return (
    <>
      <Header />
      <HeroSection isLoggedIn={isLoggedIn} />
      <SocialProofSection />

      <main id="catalog" className="mx-auto max-w-6xl px-4 py-6">
        <h2 className="mb-4 text-2xl font-bold text-gray-900">Каталог курсов</h2>

        <form onSubmit={handleSearch} className="mb-4 flex gap-2">
          <label htmlFor="search-input" className="sr-only">Поиск курсов</label>
          <input
            id="search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск курсов..."
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
          >
            Найти
          </button>
        </form>

        <div className="mb-6 flex flex-wrap items-center gap-3">
          <label htmlFor="category-select" className="sr-only">Категория</label>
          <select
            id="category-select"
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="">Все категории</option>
            {categoryList.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          <label htmlFor="level-select" className="sr-only">Уровень</label>
          <select
            id="level-select"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="">Все уровни</option>
            <option value="beginner">Начальный</option>
            <option value="intermediate">Средний</option>
            <option value="advanced">Продвинутый</option>
          </select>

          <select
            value={isFree}
            onChange={(e) => setIsFree(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="">Все курсы</option>
            <option value="true">Бесплатные</option>
            <option value="false">Платные</option>
          </select>

          <label htmlFor="sort-select" className="sr-only">Сортировка</label>
          <select
            id="sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="created_at">Новые</option>
            <option value="avg_rating">По рейтингу</option>
            <option value="price">По цене</option>
          </select>
        </div>

        {error ? (
          <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">
            {getErrorMessage(error, "Ошибка загрузки")}
          </div>
        ) : isLoading ? (
          <p className="text-center text-gray-400">Загрузка...</p>
        ) : !data || data.items.length === 0 ? (
          <p className="text-center text-gray-400">Курсы не найдены</p>
        ) : (
          <>
            <p className="mb-4 text-sm text-gray-500">
              Найдено: {data.total}
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((c) => (
                <CourseCard key={c.id} course={c} />
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}
