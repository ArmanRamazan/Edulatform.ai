"use client";

import Link from "next/link";
import * as Dialog from "@radix-ui/react-dialog";

interface PaywallDialogProps {
  open: boolean;
  onClose: () => void;
  feature?: string;
  limit?: number;
  resetAt?: string;
}

export function PaywallDialog({
  open,
  onClose,
  feature,
  limit,
  resetAt,
}: PaywallDialogProps) {
  const resetTime = resetAt
    ? new Date(resetAt).toLocaleTimeString("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl focus:outline-none">
          <Dialog.Title className="text-lg font-bold text-gray-900">
            Вы достигли дневного лимита AI
          </Dialog.Title>

          <Dialog.Description className="mt-2 text-sm text-gray-600">
            Вы использовали все {limit ?? "бесплатные"} AI-взаимодействия
            сегодня. Перейдите на тариф Student или Pro для расширенного доступа.
          </Dialog.Description>

          {feature && (
            <p className="mt-3 rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">
              Функция: <span className="font-medium">{feature}</span>
            </p>
          )}

          {resetTime && (
            <p className="mt-3 text-xs text-gray-500">
              Кредиты обновятся в {resetTime}
            </p>
          )}

          <div className="mt-6 flex gap-3">
            <Link
              href="/pricing"
              className="flex-1 rounded-lg bg-blue-600 px-4 py-2.5 text-center text-sm font-medium text-white hover:bg-blue-700"
              onClick={onClose}
            >
              Улучшить тариф
            </Link>
            <button
              onClick={onClose}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Позже
            </button>
          </div>

          <Dialog.Close asChild>
            <button
              className="absolute right-3 top-3 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              aria-label="Закрыть"
            >
              &#10005;
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
