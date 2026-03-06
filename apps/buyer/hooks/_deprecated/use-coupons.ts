"use client";

import { useMutation } from "@tanstack/react-query";
import { coupons, type DiscountResult } from "@/lib/api";

export function useValidateCoupon(token: string | null) {
  return useMutation<DiscountResult, Error, { code: string; course_id: string; amount: number }>({
    mutationFn: (data) => {
      if (!token) throw new Error("Необходима авторизация");
      return coupons.validate(token, data);
    },
  });
}
