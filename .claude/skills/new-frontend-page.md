---
name: new-frontend-page
description: Create a new page in Next.js buyer or seller app
---

# New Frontend Page Workflow

## Trigger
Use when creating a new page in apps/buyer or apps/seller.

## Before starting
1. Read existing pages in the target route group to match style
2. Read `lib/api.ts` for API client patterns
3. Read `hooks/use-*.ts` for data fetching patterns
4. Check `components/ui/` for available shadcn components

## Steps

### 1. Determine rendering strategy
- SSG (static): landing pages, marketing -- use generateStaticParams
- SSR (server): catalog, search -- use streaming + loading.tsx
- Client-side: dashboard, forms, coach -- use "use client" + hooks

### 2. Create the hook (data layer)
File: `hooks/use-<feature>.ts`
```tsx
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";

export function use<Feature>() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["<feature>"],
    queryFn: () => api.<namespace>.get<Feature>(token!),
    enabled: !!token,
  });
}
```

### 3. Create the page
File: `app/(app)/<feature>/page.tsx`
```tsx
"use client";
import { use<Feature> } from "@/hooks/use-<feature>";
import { Skeleton } from "@/components/ui/skeleton";

export function <Feature>Page() {
  const { data, isLoading, error } = use<Feature>();
  if (isLoading) return <LoadingSkeleton />;
  if (error) return <ErrorState error={error} />;
  return <<Feature>Content data={data} />;
}
```

### 4. Add loading.tsx (for SSR/streaming)
File: `app/(app)/<feature>/loading.tsx`
```tsx
import { Skeleton } from "@/components/ui/skeleton";
export default function Loading() {
  return <Skeleton className="h-96 w-full" />;
}
```

### 5. Create components
- Server Components by default
- "use client" ONLY for hooks, event handlers, browser API
- Props via `interface`, not `type`
- Named exports only

### 6. Theme compliance
- Dark-first: backgrounds #0a0a0f, #1a1a1f
- Violet accent: #7c5cfc
- Fonts: Inter (sans), JetBrains Mono (mono)
- Tailwind classes, no CSS modules

### 7. Performance
- Dynamic import for heavy components (charts, editors, modals)
- next/image for images, next/link for navigation
- Bundle budget: < 100KB gzip (buyer)

### 8. Verify
```bash
cd apps/<name> && pnpm build
```
