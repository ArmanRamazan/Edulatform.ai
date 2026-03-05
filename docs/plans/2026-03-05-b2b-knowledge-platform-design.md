# B2B Knowledge Platform — Design Document

> Date: 2026-03-05
> Status: Approved
> Scope: Frontend redesign (buyer app migration) + MCP Server + AI isolation

## Vision

EduPlatform transforms from B2C (Udemy-like) to **B2B knowledge hub**: company uploads docs/code -> platform builds knowledge graph -> AI agents create personalized missions -> engineers learn through Obsidian-like interface. MCP server enables integration with any AI tool (Cursor, Claude Desktop, custom agents).

## Target Users

- **Tech Lead** — uploads docs, manages graph, views team progress
- **Engineer** — completes missions, navigates graph, searches knowledge
- **AI Agent** (via MCP) — full CRUD on behalf of user

---

## 1. Visual Design System: "Dark Knowledge"

### Inspiration
Obsidian, Linear, Raycast, Arc Browser

### Design Principles
- Dark-first, developer-native aesthetic
- Knowledge graph as glowing neural network
- Content hierarchy through luminance (brighter = more important)
- Minimal chrome, maximum content
- Micro-animations for feedback, not decoration

### Color Palette

```
Background:
  base:       #0a0a0f    (near-black with blue undertone)
  surface:    #14141f    (cards, panels)
  elevated:   #1a1a2e    (dropdowns, modals, command palette)

Borders:
  subtle:     #1e1e2e    (dividers)
  default:    #2a2a3e    (card borders)
  focus:      #7c5cfc40  (accent glow)

Text:
  primary:    #e2e2e8    (headings, body)
  secondary:  #6b6b80    (labels, hints)
  tertiary:   #45455a    (disabled, placeholders)

Accent:
  primary:    #7c5cfc    (violet — main brand)
  hover:      #9b7eff    (lighter violet)
  pressed:    #6344e0    (darker violet)

Semantic:
  success:    #34d399    (mint green — mastery, completed)
  warning:    #fbbf24    (amber — due soon, attention)
  danger:     #f87171    (red — errors, overdue)
  info:       #38bdf8    (sky blue — links, external sources)

Graph:
  node-idle:      #3f3f46    (gray, not started)
  node-learning:  #7c5cfc    (violet, in progress) + pulse animation
  node-mastered:  #34d399    (mint, mastered) + subtle glow
  edge-default:   #2a2a3e    (dim connection)
  edge-active:    #7c5cfc60  (highlighted path)
  node-gradient:  #7c5cfc -> #3b82f6  (violet to blue)

Mastery gradient (progress bars, rings):
  0%:    #3f3f46
  25%:   #7c5cfc
  50%:   #6366f1
  75%:   #3b82f6
  100%:  #34d399
```

### Typography

| Use | Font | Weight | Size |
|-----|------|--------|------|
| Headings | Inter | 600 (semibold) | 24-32px |
| Body | Inter | 400 (regular) | 14-16px |
| Labels/Captions | Inter | 500 (medium) | 12-13px |
| Code/Data/Numbers | JetBrains Mono | 400-500 | 13-14px |
| Large metrics (XP, %) | JetBrains Mono | 700 (bold) | 28-48px |

### Component Styles

**Cards:**
- Background: surface (#14141f)
- Border: 1px solid #1e1e2e
- Border-radius: 12px
- On hover: border transitions to #2a2a3e, subtle backdrop-blur
- No box-shadow in default state
- Active/selected: left border 2px accent

**Buttons:**
- Primary: bg accent (#7c5cfc), text white, hover #9b7eff, glow shadow on hover
- Secondary: bg transparent, border #2a2a3e, text #e2e2e8, hover bg #1a1a2e
- Ghost: no border, text secondary, hover text primary
- Destructive: bg #f8717120, text #f87171, hover bg #f8717130
- Border-radius: 8px
- Height: 36px (default), 32px (small), 40px (large)
- Transition: 150ms ease

**Inputs:**
- Background: #0a0a0f (base)
- Border: 1px solid #1e1e2e
- Focus: border accent + box-shadow 0 0 0 3px #7c5cfc20
- Border-radius: 8px
- Text: primary
- Placeholder: tertiary

**Command Palette (Cmd+K):**
- Overlay: bg black/60 + backdrop-blur-xl
- Panel: elevated bg, border subtle, max-width 640px
- Input at top, results grouped by category
- Keyboard navigation with highlight bar
- Categories: Internal Docs, External, Concepts, Missions, Actions

**Badges/Pills:**
- Small rounded-full, px-2 py-0.5
- Color coded by type:
  - Trust level: accent gradient
  - Source type: internal=violet, external=sky, mission=mint
  - Status: success/warning/danger

**Progress Bars:**
- Height: 4px (compact) or 8px (featured)
- Background: #1e1e2e
- Fill: mastery gradient (animated on mount)
- Border-radius: full

**Toast/Notifications:**
- Elevated bg, left border 3px colored by type
- Slide-in from top-right, auto-dismiss 5s

### Animations

| Element | Animation | Duration | Library |
|---------|-----------|----------|---------|
| Page transitions | Fade + slight Y translate | 200ms | Framer Motion |
| Card mount | Fade in + scale from 0.97 | 300ms | Framer Motion |
| Numbers (XP, %) | Count-up on mount | 600ms | Framer Motion |
| Progress bars | Width animate from 0 | 500ms ease-out | CSS transition |
| Graph nodes | Pulse on "learning" state | 2s infinite | CSS keyframes |
| Graph mastered glow | Subtle radial glow | static | CSS box-shadow |
| Hover states | All interactive elements | 150ms ease | CSS transition |
| Command palette | Scale from 0.95 + fade | 150ms | Framer Motion |
| Skeleton loaders | Shimmer gradient animation | 1.5s infinite | CSS keyframes |

### Graph Visual Design

- Canvas: base background (#0a0a0f), full-width section
- Nodes: circles 32-48px depending on importance (connection count)
- Node label: below node, Inter 12px, secondary color
- Node color: by mastery state (idle/learning/mastered)
- Edges: curved bezier, 1px, default dim (#2a2a3e)
- On hover node: connected edges brighten, unrelated dim further
- On click node: zoom + pan to center, expand to show mini-card
- Minimap: bottom-right corner, semi-transparent
- Controls: zoom in/out, fit view, fullscreen toggle

---

## 2. Navigation & Route Architecture

### Migration approach
Gradual rework of `apps/buyer`. Add org-context, new B2B screens. Hide B2C pages.

### New route structure

```
/ (landing — keep for marketing, light theme override)
/login, /register (keep, restyle to dark theme)
/org/select              — org picker after login (NEW)
/dashboard               — B2B dashboard with missions (REWORK)
/graph                   — interactive knowledge graph (NEW)
/graph/[conceptId]       — concept hub aggregator (NEW)
/search                  — smart search with routing (NEW)
/missions                — mission history (REWORK from enrollments)
/missions/[id]           — active mission + coach (REWORK from lessons)
/settings                — org settings, LLM provider config (NEW)
/settings/llm            — LLM provider configuration (NEW)
/settings/team           — team management (NEW)
```

**Kept as-is:** auth flow, notifications, messages, badges, profile
**Hidden/removed later:** courses catalog, bundles, wishlist, payments (B2C)

### Layout

```
RootLayout
  ├─ Sidebar (left, collapsible, 64px collapsed / 240px expanded)
  │   ├─ Org logo + name
  │   ├─ Navigation links (icons + labels)
  │   │   ├─ Dashboard
  │   │   ├─ Graph
  │   │   ├─ Search (+ Cmd+K shortcut hint)
  │   │   ├─ Missions
  │   │   ├─ Flashcards
  │   │   ├─ Messages
  │   │   └─ Settings (bottom)
  │   ├─ Trust level indicator (bottom)
  │   └─ User avatar + name (bottom)
  │
  └─ Main content area (scrollable)
      ├─ Top bar (breadcrumbs + Cmd+K trigger + notifications bell)
      └─ Page content
```

---

## 3. Page Designs

### 3.1 Dashboard (Priority: FIRST)

Endpoint-driven blocks. Each block = one hook + one API call + independent loading/error state.

```
DashboardPage
  ├─ GreetingBlock          → GET /daily/me
  │   "Good morning, Arman. Day 12 streak."
  │   Large streak number in JetBrains Mono + streak flame icon
  │
  ├─ MissionBlock           → GET /ai/mission/daily
  │   Today's mission card: concept name, difficulty badge, estimated time
  │   "Start Mission" primary button with glow
  │   If completed: score + mastery delta with count-up animation
  │
  ├─ TrustLevelBlock        → GET /trust-level/me
  │   Current level (0-5) as ring/arc chart with gradient fill
  │   Progress to next level: "12/30 missions to Contributor"
  │   Unlocked areas list
  │
  ├─ FlashcardsBlock        → GET /flashcards/due
  │   Due count as large number
  │   "Review N cards" button
  │   Next review time if 0 due
  │
  ├─ StreakBlock             → GET /streaks/me
  │   Weekly heatmap (7 cells, Mon-Sun)
  │   Current + longest streak
  │
  ├─ MasteryOverviewBlock   → GET /concepts/mastery (top 10)
  │   Horizontal bar chart: concept name + mastery %
  │   Color by mastery gradient
  │
  ├─ TeamProgressBlock      → GET /trust-level/org/{org_id}
  │   (Tech Lead only)
  │   Team members: avatar + name + trust level badge
  │   Avg mastery across org
  │
  └─ RecentActivityBlock    → GET /activity/feed
      Last 5 activities: icon + description + timestamp
      "View all" link to /feed
```

### 3.2 Knowledge Graph

```
GraphPage
  ├─ GraphCanvas (full width, 70vh)
  │   → GET /kb/{org_id}/concepts (nodes + edges)
  │   React Flow with custom node components
  │   Color by mastery state
  │   Click node → navigate to /graph/[conceptId]
  │   Search overlay: filter/highlight nodes
  │
  ├─ GraphControls (floating top-right)
  │   Zoom, fit, fullscreen, layout toggle (force/tree/radial)
  │
  └─ GraphSidebar (right, 320px, collapsible)
      On node hover: preview card with name, mastery, connected count
      On node select: mini concept hub (sources count, missions count)
      Quick actions: start mission, view hub
```

### 3.3 Concept Hub

```
ConceptHubPage (/graph/[conceptId])
  ├─ ConceptHeader
  │   ├─ Breadcrumb: Graph > Category > Concept Name
  │   ├─ Title (h1) + description
  │   ├─ Mastery ring (large, animated)
  │   ├─ Prerequisites (linked concept pills, clickable)
  │   └─ Dependents ("Unlocks: X, Y, Z" pills)
  │
  ├─ InternalSourcesBlock   → POST /kb/{org_id}/search
  │   Cards: doc title, type badge (code/doc/config), snippet, file path
  │   Click → link to original (repo URL, wiki page, etc.)
  │
  ├─ ExternalSourcesBlock   → POST /ai/search/external
  │   Cards: title, URL, snippet, source domain
  │   Opens in new tab
  │
  ├─ MissionsBlock          → GET /missions/me?concept_id=X
  │   Completed: score + date
  │   Available: difficulty + estimated time + "Start" button
  │
  ├─ TeamMasteryBlock       → GET /trust-level/org/{org_id}
  │   (Tech Lead only)
  │   Who mastered, who learning, who not started
  │
  ├─ DiscussionsBlock       → GET /discussions?concept_id=X
  │   Threaded comments, reply, upvote
  │
  └─ RelatedGraphBlock      → GET /kb/{org_id}/concepts (filtered 1-hop)
      Mini graph: this concept + immediate neighbors
      Click neighbor → navigate to its hub
```

### 3.4 Smart Search

```
SearchPage (/search)   — also accessible via Cmd+K
  ├─ SearchInput
  │   Full-width, large, autofocus
  │   Concept name suggestions as user types
  │
  ├─ RouteIndicator
  │   Pill showing routing decision: "Internal + External" / "Internal only"
  │
  ├─ InternalResults        → POST /kb/{org_id}/search
  │   Section header: "From your knowledge base" + violet dot
  │   Cards: source type icon, title, snippet, file path/URL
  │
  └─ ExternalResults        → POST /ai/search/external
      Section header: "From the web" + sky dot
      Cards: title, domain, snippet, URL
      Each result has "Save to KB" action (imports as document)
```

### 3.5 Active Mission

```
MissionPage (/missions/[id])
  ├─ MissionHeader
  │   Concept name, difficulty, phase indicator (5 dots)
  │   Timer (elapsed), "End Session" button
  │
  ├─ ContentArea (left, 60%)
  │   Phase-dependent content:
  │   - Recap: key points from previous session
  │   - Reading: RAG snippets with source links
  │   - Questions: interactive MCQ cards
  │   - Code Case: code editor (Monaco) + test runner
  │   - Wrap-up: summary + mastery delta
  │
  └─ CoachChat (right, 40%)
      Chat interface: messages + input
      Phase indicator synced with content
      Socratic hints, not direct answers
      "I'm stuck" button → hint
```

---

## 4. Smart Search — Data Isolation Architecture

### AI Router (query classification)

```
User query
  → Classifier (rule-based MVP, LLM-based later)
  │
  ├─ Internal signals: "our", "we", "internal", company terms, file paths
  │   → INTERNAL ONLY (RAG search, never leaves org boundary)
  │
  ├─ External signals: library names, "how to", "best practice", generic tech terms
  │   → EXTERNAL ONLY (Gemini web grounding, only user query text sent)
  │
  └─ Mixed signals: "how we implemented X and best practices"
      → BOTH (parallel: RAG internal + Gemini external, separate prompts)
```

### Isolation guarantees

| Route | What is sent to external API | What stays local |
|-------|------------------------------|-----------------|
| INTERNAL | Nothing | Query + RAG chunks + LLM processing (if self-hosted) |
| EXTERNAL | User query text only | Nothing (no internal context in prompt) |
| BOTH | User query text only (to external) | RAG chunks (to internal LLM) |

Results merged **only on frontend**. Backend never combines internal chunks with external API calls in same prompt.

---

## 5. MCP Server

### Architecture

Separate process (`services/rs/mcp-server` or `services/py/mcp`), authenticates via user JWT.

### Tools (Full CRUD)

| Tool | Method | Endpoint | Scope |
|------|--------|----------|-------|
| `search_knowledge` | POST | /kb/{org_id}/search | Read |
| `search_web` | POST | /ai/search/external | Read |
| `get_concept` | GET | /concepts/{id} | Read |
| `get_concept_graph` | GET | /kb/{org_id}/concepts | Read |
| `get_mastery` | GET | /concepts/mastery | Read |
| `get_daily_summary` | GET | /daily/me | Read |
| `get_flashcards_due` | GET | /flashcards/due | Read |
| `start_mission` | GET | /ai/mission/daily | Read+Action |
| `complete_mission` | POST | /ai/mission/complete | Action |
| `coach_chat` | POST | /ai/coach/chat | Action |
| `review_flashcard` | POST | /flashcards/review | Action |
| `create_document` | POST | /documents | Write |
| `create_concept` | POST | /concepts | Write |
| `update_concept` | PUT | /concepts/{id} | Write |
| `delete_concept` | DELETE | /concepts/{id} | Write |
| `add_relationship` | POST | /concepts/prerequisite | Write |

### MCP Resources

| Resource | URI | Description |
|----------|-----|-------------|
| `knowledge://graph` | /kb/{org_id}/concepts | Full concept graph |
| `knowledge://concept/{id}` | /concepts/{id} | Single concept |
| `progress://daily` | /daily/me | Today's summary |
| `progress://mastery` | /concepts/mastery | All mastery levels |
| `progress://trust-level` | /trust-level/me | Current trust level |

### Security
- JWT token passed per-session (user configures in MCP client)
- All org-scoped requests verify membership via existing middleware
- MCP server never proxies raw internal chunks to external LLMs
- Agent receives processed results, not raw document content
- Write operations require trust level >= 2 (Practitioner)

---

## 6. Configurable LLM Provider (per org)

### New endpoint: GET/PUT /org/{org_id}/settings/llm

```json
{
  "internal_provider": "self_hosted | gemini",
  "internal_model_url": "http://...",
  "external_provider": "gemini",
  "embedding_provider": "gemini | self_hosted",
  "data_isolation": "strict | standard"
}
```

- **strict**: internal data never sent to external API. Requires self-hosted LLM.
- **standard**: internal data processed via Gemini API (ToS compliant, no training).

### Provider abstraction (backend)

```python
# services/py/ai/app/services/llm_provider.py
class LLMProvider(ABC):
    async def complete(self, prompt: str, context: str) -> str: ...
    async def embed(self, text: str) -> list[float]: ...

class GeminiProvider(LLMProvider): ...
class SelfHostedProvider(LLMProvider): ...  # vLLM / Ollama compatible
```

AI service resolves provider per org_id from settings.

---

## 7. UI Kit — Technology Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Primitives | shadcn/ui | Copyable Radix + Tailwind components, full style control |
| Graph | @xyflow/react (React Flow) | Interactive graphs, custom nodes, zoom/pan |
| Animations | Framer Motion | Page transitions, mount animations, count-up |
| Icons | Lucide React | Consistent icon set (part of shadcn) |
| Charts | Recharts (already present) | Mastery trends, velocity |
| Theme | next-themes | Dark mode (primary), optional light override |
| Command palette | cmdk (part of shadcn) | Cmd+K search |
| Code editor | Monaco Editor (dynamic import) | Code cases in missions |
| Fonts | next/font | Inter + JetBrains Mono, no external CDN |

---

## 8. Migration Phases

| Phase | Scope | Depends on | New endpoints needed |
|-------|-------|------------|---------------------|
| **1** | Dashboard rework (B2B, org-context, endpoint-driven blocks) | Backend exists | None (all endpoints exist) |
| **2** | Org selector + shadcn/ui setup + dark theme | Phase 1 | GET/PUT /org/{org_id}/settings |
| **3** | Knowledge Graph page (interactive, React Flow) | Phase 2 | None (GET /kb/{org_id}/concepts exists) |
| **4** | Concept Hub page (aggregator) | Phase 3 | None (all search/mission endpoints exist) |
| **5** | Smart Search (internal + external with isolation) | Phase 4 | POST /ai/search/external (NEW) |
| **6** | Mission rework (5-phase with coach chat) | Phase 4 | None (coach endpoints exist) |
| **7** | MCP Server (user-facing, Full CRUD) | Phase 5 | MCP protocol layer (NEW service) |
| **8** | LLM Provider config (per org) | Phase 7 | GET/PUT /org/{org_id}/settings/llm (NEW) |
| **9** | Remove B2C pages, cleanup | All above | None |

### New backend work required

1. `POST /ai/search/external` — web search via Gemini grounding (AI service)
2. `GET/PUT /org/{org_id}/settings` — org configuration (Identity or new Org service)
3. `GET/PUT /org/{org_id}/settings/llm` — LLM provider config (AI service)
4. MCP Server service — new service wrapping existing endpoints
5. `LLMProvider` abstraction — refactor AI service to support pluggable providers
