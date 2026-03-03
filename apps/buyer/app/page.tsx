import { Header } from "@/components/Header";
import { HeroCTA } from "@/components/HeroCTA";
import { CatalogSection } from "@/components/CatalogSection";

function HeroSection() {
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
          <HeroCTA />
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

function SocialProofSection() {
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
  return (
    <>
      <Header />
      <HeroSection />
      <SocialProofSection />
      <main>
        <CatalogSection />
      </main>
    </>
  );
}
