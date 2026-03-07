import Link from "next/link";
import { Sparkles } from "lucide-react";

const PLATFORM_LINKS = [
  { label: "Features", href: "/#features" },
  { label: "Pricing", href: "/pricing" },
  { label: "For Teams", href: "/register" },
] as const;

const PRODUCT_LINKS = [
  { label: "Knowledge Graph", href: "/graph" },
  { label: "AI Coach", href: "/dashboard" },
  { label: "Flashcards", href: "/flashcards" },
  { label: "Missions", href: "/dashboard" },
] as const;

const INFO_LINKS = [
  { label: "Help", href: "#" },
  { label: "Terms", href: "#" },
  { label: "Privacy", href: "#" },
] as const;

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: ReadonlyArray<{ label: string; href: string }>;
}) {
  return (
    <div>
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      <ul className="space-y-2">
        {links.map((link) => (
          <li key={link.href + link.label}>
            <Link
              href={link.href}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
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
    <footer className="border-t border-border bg-card">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-4">
          <div>
            <Link href="/" className="mb-3 flex items-center gap-2 text-sm font-bold text-foreground">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
                <Sparkles className="h-3 w-3 text-primary-foreground" />
              </div>
              KnowledgeOS
            </Link>
            <p className="text-xs leading-relaxed text-muted-foreground">
              AI-powered knowledge platform for engineering teams.
            </p>
          </div>
          <FooterColumn title="Platform" links={PLATFORM_LINKS} />
          <FooterColumn title="Product" links={PRODUCT_LINKS} />
          <FooterColumn title="Info" links={INFO_LINKS} />
        </div>

        <div className="mt-10 border-t border-border pt-6">
          <p className="text-center text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} KnowledgeOS. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
