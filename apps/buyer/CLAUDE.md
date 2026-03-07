# Buyer App (B2B Knowledge Platform)

Port 3001 | Next.js 15 | React 19 | TypeScript strict

## Theme: Dark Knowledge

- Dark-first UI, violet accent (#7c5cfc)
- Backgrounds: #0a0a0f (base), #1a1a1f (elevated)
- Fonts: Inter (sans) + JetBrains Mono (mono)
- CSS variables in app/globals.css

## Layout

- `(app)/` route group: authenticated, sidebar + topbar layout
- `(marketing)/` route group: public, landing pages

## Key dependencies

- `@xyflow/react` + `dagre` — React Flow knowledge graph
- `@tanstack/react-query` v5 — server state
- `@stripe/react-stripe-js` — payment integration
- `recharts` — analytics charts
- `cmdk` — command palette
- `framer-motion` — animations
- `radix-ui` + `shadcn` — UI primitives
- `lucide-react` — icons

## API proxy (next.config.ts rewrites)

All 8 backend services proxied:
- /api/identity/* -> localhost:8001
- /api/course/* -> localhost:8002
- /api/enrollment/* -> localhost:8003
- /api/payment/* -> localhost:8004
- /api/notification/* -> localhost:8005
- /api/ai/* -> localhost:8006
- /api/learning/* -> localhost:8007
- /api/rag/* -> localhost:8008

## Rules

- Server Components by default, `"use client"` only when needed
- Only named exports, no default exports, no index.tsx barrels
- `next/image` and `next/link` only — no raw `<img>` or `<a>`
- Dynamic import for heavy components (charts, graph, video player)

## Verify

```bash
cd apps/buyer && pnpm build
```
