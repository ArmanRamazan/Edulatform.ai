"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  BarChart3,
  CreditCard,
  User,
  Bell,
  ChevronRight,
  Settings,
} from "lucide-react";

const settingsLinks = [
  {
    title: "Team Analytics",
    description: "Track your team's knowledge progress and identify gaps",
    href: "/settings/analytics",
    icon: BarChart3,
    enabled: true,
  },
  {
    title: "Billing & Subscription",
    description: "Manage your plan, payment methods, and invoices",
    href: "/settings/billing",
    icon: CreditCard,
    enabled: true,
  },
  {
    title: "Profile",
    description: "Update your personal information and preferences",
    href: "#",
    icon: User,
    enabled: false,
  },
  {
    title: "Notifications",
    description: "Configure email and in-app notification settings",
    href: "#",
    icon: Bell,
    enabled: false,
  },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07 },
  },
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Settings className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Manage your workspace and account preferences
          </p>
        </div>
      </div>

      {/* Cards grid */}
      <motion.div
        className="grid gap-4 sm:grid-cols-2"
        variants={container}
        initial="hidden"
        animate="show"
      >
        {settingsLinks.map((link) => {
          const Icon = link.icon;
          const content = (
            <motion.div
              key={link.title}
              variants={item}
              className={`group relative rounded-xl border p-5 transition-colors ${
                link.enabled
                  ? "border-white/[0.06] bg-[#14141f] hover:border-[#7c5cfc]/30 hover:bg-[#14141f]/80 cursor-pointer"
                  : "border-white/[0.04] bg-[#14141f]/50 opacity-50 cursor-default"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                      link.enabled ? "bg-[#7c5cfc]/10" : "bg-white/[0.04]"
                    }`}
                  >
                    <Icon
                      className={`h-4.5 w-4.5 ${
                        link.enabled
                          ? "text-[#7c5cfc]"
                          : "text-muted-foreground"
                      }`}
                    />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">
                      {link.title}
                    </h2>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                      {link.description}
                    </p>
                  </div>
                </div>
                {link.enabled ? (
                  <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-[#7c5cfc]" />
                ) : (
                  <span className="mt-1 shrink-0 rounded-full bg-white/[0.06] px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                    Soon
                  </span>
                )}
              </div>
            </motion.div>
          );

          if (link.enabled) {
            return (
              <Link key={link.title} href={link.href} className="block">
                {content}
              </Link>
            );
          }
          return content;
        })}
      </motion.div>
    </div>
  );
}
