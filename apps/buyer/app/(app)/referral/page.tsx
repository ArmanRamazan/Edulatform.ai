"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useReferralInfo } from "@/hooks/use-referral";
import { Header } from "@/components/Header";

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      onClick={handleCopy}
      className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
    >
      {copied ? "Скопировано!" : label}
    </button>
  );
}

export default function ReferralPage() {
  const { user, token, loading } = useAuth();
  const referral = useReferralInfo(token);

  if (loading) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-2xl px-4 py-12">
          <p className="text-center text-gray-500">Загрузка...</p>
        </main>
      </>
    );
  }

  if (!user) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-2xl px-4 py-12">
          <p className="text-center text-gray-500">Войдите, чтобы увидеть реферальную программу.</p>
        </main>
      </>
    );
  }

  const referralCode = referral.data?.referral_code ?? "";
  const referralLink = referralCode
    ? `https://eduplatform.ru/register?ref=${referralCode}`
    : "";

  const telegramUrl = referralLink
    ? `https://t.me/share/url?url=${encodeURIComponent(referralLink)}&text=${encodeURIComponent("Присоединяйся к EduPlatform!")}`
    : "";

  const vkUrl = referralLink
    ? `https://vk.com/share.php?url=${encodeURIComponent(referralLink)}`
    : "";

  return (
    <>
      <Header />
      <main className="mx-auto max-w-2xl px-4 py-12">
        <h1 className="mb-8 text-2xl font-bold">Пригласите друзей</h1>

        {referral.isLoading ? (
          <p className="text-gray-500">Загрузка данных...</p>
        ) : referral.isError ? (
          <p className="text-red-500">Не удалось загрузить данные реферальной программы.</p>
        ) : (
          <>
            {/* Referral link section */}
            <section className="mb-8 rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-4 text-lg font-semibold">Ваша реферальная ссылка</h2>

              <div className="mb-3">
                <p className="mb-1 text-sm text-gray-500">Ваш код:</p>
                <div className="flex items-center gap-3">
                  <code className="rounded bg-gray-100 px-3 py-2 font-mono text-sm">
                    {referralCode}
                  </code>
                  <CopyButton text={referralCode} label="Копировать" />
                </div>
              </div>

              <div className="mb-4">
                <p className="mb-1 text-sm text-gray-500">Ваша ссылка:</p>
                <div className="flex items-center gap-3">
                  <code className="truncate rounded bg-gray-100 px-3 py-2 font-mono text-sm">
                    {referralLink}
                  </code>
                  <CopyButton text={referralLink} label="Копировать" />
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <CopyButton text={referralLink} label="Скопировать ссылку" />
                <a
                  href={telegramUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded bg-sky-500 px-3 py-1 text-sm text-white hover:bg-sky-600"
                >
                  Поделиться в Telegram
                </a>
                <a
                  href={vkUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded bg-blue-800 px-3 py-1 text-sm text-white hover:bg-blue-900"
                >
                  Поделиться в VK
                </a>
              </div>
            </section>

            {/* Stats section */}
            <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
                <p className="text-3xl font-bold text-blue-600">
                  {referral.data?.invited_count ?? 0}
                </p>
                <p className="mt-1 text-sm text-gray-500">Приглашено</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
                <p className="text-3xl font-bold text-green-600">
                  {referral.data?.completed_count ?? 0}
                </p>
                <p className="mt-1 text-sm text-gray-500">Завершили курс</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
                <p className="text-3xl font-bold text-purple-600">
                  {referral.data?.rewards_earned ?? 0}
                </p>
                <p className="mt-1 text-sm text-gray-500">Награды</p>
              </div>
            </section>

            {/* How it works */}
            <section className="rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-4 text-lg font-semibold">Как это работает</h2>
              <ol className="space-y-4">
                <li className="flex gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-600">
                    1
                  </span>
                  <div>
                    <p className="font-medium">Поделитесь ссылкой с другом</p>
                    <p className="text-sm text-gray-500">
                      Отправьте вашу реферальную ссылку через мессенджер или соцсети.
                    </p>
                  </div>
                </li>
                <li className="flex gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-600">
                    2
                  </span>
                  <div>
                    <p className="font-medium">Друг регистрируется по вашей ссылке</p>
                    <p className="text-sm text-gray-500">
                      При регистрации реферальный код применяется автоматически.
                    </p>
                  </div>
                </li>
                <li className="flex gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-600">
                    3
                  </span>
                  <div>
                    <p className="font-medium">Друг завершает первый курс — оба получаете бонус</p>
                    <p className="text-sm text-gray-500">
                      Награда начисляется после завершения первого курса приглашённым другом.
                    </p>
                  </div>
                </li>
              </ol>
            </section>
          </>
        )}
      </main>
    </>
  );
}
