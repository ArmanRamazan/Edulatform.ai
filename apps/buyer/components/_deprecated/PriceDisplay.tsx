import { type DiscountResult } from "@/lib/api";

interface PriceDisplayProps {
  originalPrice: number;
  discount?: DiscountResult | null;
}

export function PriceDisplay({ originalPrice, discount }: PriceDisplayProps) {
  if (!discount) {
    return <span className="text-lg font-bold">${originalPrice}</span>;
  }

  return (
    <span className="flex items-center gap-2">
      <span className="text-sm text-gray-400 line-through">${discount.original_price}</span>
      <span className="text-lg font-bold text-green-700">${discount.final_price}</span>
      <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">
        {discount.coupon_code}
      </span>
    </span>
  );
}
