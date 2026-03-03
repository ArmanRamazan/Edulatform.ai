import Link from "next/link";

const PLATFORM_LINKS = [
  { label: "О нас", href: "/about" },
  { label: "Каталог курсов", href: "/courses" },
  { label: "Тарифы", href: "/pricing" },
  { label: "Для преподавателей", href: "/seller" },
] as const;

const LEARNING_LINKS = [
  { label: "AI-тьютор", href: "/courses" },
  { label: "Флеш-карточки", href: "/flashcards" },
  { label: "Квизы", href: "/quizzes" },
  { label: "Достижения", href: "/badges" },
] as const;

const INFO_LINKS = [
  { label: "Помощь", href: "#" },
  { label: "Контакты", href: "#" },
  { label: "Условия использования", href: "#" },
  { label: "Политика конфиденциальности", href: "#" },
] as const;

function FooterColumn({ title, links }: { title: string; links: ReadonlyArray<{ label: string; href: string }> }) {
  return (
    <div>
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
        {title}
      </h3>
      <ul className="space-y-2">
        {links.map((link) => (
          <li key={link.href + link.label}>
            <Link
              href={link.href}
              className="text-sm text-gray-400 transition-colors hover:text-white"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-gray-800 bg-gray-900">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
          <FooterColumn title="Платформа" links={PLATFORM_LINKS} />
          <FooterColumn title="Обучение" links={LEARNING_LINKS} />
          <FooterColumn title="Информация" links={INFO_LINKS} />
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-gray-800 pt-6 sm:flex-row">
          <p className="text-sm text-gray-500">
            &copy; 2025 EduPlatform. Все права защищены.
          </p>
          <div className="flex gap-4">
            <a
              href="#"
              className="text-sm text-gray-500 transition-colors hover:text-white"
              aria-label="Telegram"
            >
              Telegram
            </a>
            <a
              href="#"
              className="text-sm text-gray-500 transition-colors hover:text-white"
              aria-label="VK"
            >
              VK
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
