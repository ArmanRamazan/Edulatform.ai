"use client";

import Link from "next/link";
import { Header } from "@/components/Header";
import { CourseCard } from "@/components/CourseCard";
import { CourseCardSkeleton } from "@/components/CourseCardSkeleton";
import { useAuth } from "@/hooks/use-auth";
import { useMyWishlist } from "@/hooks/use-wishlist";

export default function WishlistPage() {
  const { token, loading: authLoading } = useAuth();
  const { data, isLoading } = useMyWishlist(token);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold">Избранное</h1>

        {(authLoading || isLoading) && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <CourseCardSkeleton key={i} />
            ))}
          </div>
        )}

        {!authLoading && !token && (
          <p className="text-center text-gray-500">
            <Link href="/login" className="text-blue-600 hover:underline">
              Войдите
            </Link>
            , чтобы сохранять курсы в избранное.
          </p>
        )}

        {!authLoading && token && !isLoading && (!data || data.items.length === 0) && (
          <div className="text-center">
            <p className="mb-4 text-gray-500">
              Нет сохранённых курсов — найдите что-нибудь интересное!
            </p>
            <Link
              href="/courses"
              className="inline-block rounded-lg bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-700"
            >
              Перейти к каталогу
            </Link>
          </div>
        )}

        {data && data.items.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((item) => (
              <CourseCard key={item.id} course={item.course} token={token} />
            ))}
          </div>
        )}
      </main>
    </>
  );
}
