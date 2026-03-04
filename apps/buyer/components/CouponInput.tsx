"use client";

import { useState } from "react";
import { type DiscountResult } from "@/lib/api";
import { useValidateCoupon } from "@/hooks/use-coupons";
import { getErrorMessage } from "@/lib/errors";

interface CouponInputProps {
  courseId: string;
  coursePrice: number;
  token: string | null;
  onCouponApplied: (discount: DiscountResult | null) => void;
}

export function CouponInput({ courseId, coursePrice, token, onCouponApplied }: CouponInputProps) {
  const [expanded, setExpanded] = useState(false);
  const [code, setCode] = useState("");
  const [applied, setApplied] = useState<DiscountResult | null>(null);

  const validate = useValidateCoupon(token);

  function handleApply() {
    if (!code.trim()) return;
    validate.mutate(
      { code: code.trim(), course_id: courseId, amount: coursePrice },
      {
        onSuccess: (result) => {
          setApplied(result);
          onCouponApplied(result);
        },
      },
    );
  }

  function handleRemove() {
    setApplied(null);
    setCode("");
    validate.reset();
    onCouponApplied(null);
  }

  if (!expanded) {
    return (
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="text-sm text-blue-600 hover:underline"
      >
        У вас есть промокод?
      </button>
    );
  }

  if (applied) {
    return (
      <div className="flex items-center gap-2 rounded border border-green-200 bg-green-50 px-3 py-2">
        <svg className="h-4 w-4 text-green-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        <span className="text-sm text-green-700">
          {applied.coupon_code} — скидка {applied.discount_amount} ₽
        </span>
        <button
          type="button"
          onClick={handleRemove}
          className="ml-auto text-sm text-red-500 hover:underline"
        >
          Удалить
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <label htmlFor="coupon-code" className="sr-only">Промокод</label>
        <input
          id="coupon-code"
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="Введите промокод"
          disabled={validate.isPending}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm uppercase placeholder:normal-case focus:border-blue-500 focus:outline-none"
          aria-describedby={validate.isError ? "coupon-error" : undefined}
        />
        <button
          type="button"
          onClick={handleApply}
          disabled={validate.isPending || !code.trim()}
          className="rounded bg-gray-800 px-3 py-1.5 text-sm text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {validate.isPending ? (
            <span className="flex items-center gap-1">
              <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              Проверка...
            </span>
          ) : (
            "Применить"
          )}
        </button>
      </div>
      {validate.isError && (
        <p id="coupon-error" className="text-sm text-red-500" role="alert">
          {getErrorMessage(validate.error, "Промокод не найден или истёк")}
        </p>
      )}
    </div>
  );
}
