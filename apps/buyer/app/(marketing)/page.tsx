import Link from "next/link";
import {
  Brain,
  Layers,
  Rocket,
  Shield,
  Sparkles,
  Target,
  Users,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

function HeroSection() {
  return (
    <section className="relative overflow-hidden border-b border-border px-4 py-24 sm:py-32">
      {/* Subtle grid background */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(124,92,252,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(124,92,252,0.3) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />
      {/* Radial glow */}
      <div className="pointer-events-none absolute left-1/2 top-0 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-primary/5 blur-[120px]" />

      <div className="relative mx-auto max-w-4xl text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5 text-xs font-medium text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          AI-powered knowledge platform
        </div>
        <h1 className="mb-5 text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
          Master any tech stack with{" "}
          <span className="bg-gradient-to-r from-primary to-[#a78bfa] bg-clip-text text-transparent">
            AI coaching
          </span>
        </h1>
        <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground">
          Knowledge graph, adaptive missions, spaced repetition, and a tri-agent AI coach —
          all in one platform for engineering teams.
        </p>

        <div className="flex items-center justify-center gap-4">
          <Button asChild size="lg" className="gap-2 px-8">
            <Link href="/register">
              Start free
              <Rocket className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="px-8">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  {
    icon: Brain,
    title: "Tri-Agent AI Coach",
    desc: "Strategist, Designer, and Coach work together to create personalized learning missions.",
  },
  {
    icon: Layers,
    title: "Knowledge Graph",
    desc: "Visualize concept relationships and track mastery across your entire tech stack.",
  },
  {
    icon: Zap,
    title: "FSRS Flashcards",
    desc: "Spaced repetition with the FSRS algorithm — review only what you're about to forget.",
  },
  {
    icon: Target,
    title: "Adaptive Missions",
    desc: "AI-generated challenges that match your skill level and focus on knowledge gaps.",
  },
  {
    icon: Users,
    title: "Team Analytics",
    desc: "Concept coverage heatmaps, bottleneck reports, and onboarding progress for tech leads.",
  },
  {
    icon: Shield,
    title: "Trust Levels",
    desc: "Earn trust through consistent learning — unlock features as your expertise grows.",
  },
] as const;

function FeaturesSection() {
  return (
    <section className="border-b border-border px-4 py-20">
      <div className="mx-auto max-w-5xl">
        <div className="mb-12 text-center">
          <h2 className="mb-3 text-2xl font-bold text-foreground sm:text-3xl">
            Built for engineering teams
          </h2>
          <p className="text-muted-foreground">
            Everything your team needs to onboard faster and learn deeper.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <Card key={f.title} className="border-border bg-card transition-colors hover:border-primary/30">
              <CardContent className="p-6">
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <f.icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="mb-2 font-semibold text-foreground">{f.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{f.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function StatsSection() {
  const stats = [
    { value: "10", label: "Microservices" },
    { value: "1408", label: "Tests passing" },
    { value: "188", label: "API endpoints" },
    { value: "47", label: "Concepts tracked" },
  ];

  return (
    <section className="border-b border-border px-4 py-16">
      <div className="mx-auto grid max-w-4xl grid-cols-2 gap-8 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="text-center">
            <p className="text-3xl font-bold text-primary">{s.value}</p>
            <p className="mt-1 text-sm text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className="px-4 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="mb-4 text-2xl font-bold text-foreground sm:text-3xl">
          Ready to level up your team?
        </h2>
        <p className="mb-8 text-muted-foreground">
          Start with a free account. No credit card required.
        </p>
        <Button asChild size="lg" className="gap-2 px-10">
          <Link href="/register">
            Get started
            <Rocket className="h-4 w-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}

export default function HomePage() {
  return (
    <>
      <MarketingHeader />
      <HeroSection />
      <FeaturesSection />
      <StatsSection />
      <CTASection />
    </>
  );
}

function MarketingHeader() {
  return (
    <header className="border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold text-foreground">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          KnowledgeOS
        </Link>

        <nav className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link href="/login">Sign in</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/register">Get started</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
