# Dark Knowledge Design System

Dark-first design system for the buyer app, inspired by Obsidian/Linear/Raycast.

## Stack

- **shadcn/ui** (New York style) — accessible component primitives
- **Tailwind CSS v4** — utility-first styling with CSS variables
- **next-themes** — theme management (dark forced for now)
- **framer-motion** — animations (available, not yet integrated)

## Color Palette

| Token       | Hex       | Usage                          |
|-------------|-----------|--------------------------------|
| background  | `#0a0a0f` | Page background                |
| card        | `#14141f` | Card surfaces                  |
| popover     | `#1a1a2e` | Dropdowns, popovers            |
| primary     | `#7c5cfc` | Buttons, links, focus rings    |
| muted       | `#22223a` | Disabled, secondary surfaces   |
| border      | `#1e1e2e` | Borders, dividers              |
| destructive | `#f87171` | Errors, delete actions         |
| success     | `#34d399` | Success states                 |
| warning     | `#fbbf24` | Warnings                       |
| info        | `#38bdf8` | Info states                    |

## Fonts

- **Inter** (400–700) — UI text (`font-sans`)
- **JetBrains Mono** (400–700) — Code blocks (`font-mono`)

Both loaded locally via `next/font/local` for reliability.

## Components

15 shadcn components installed in this directory:
avatar, badge, button, card, command, dialog, dropdown-menu,
input, progress, scroll-area, separator, sheet, skeleton, tabs, tooltip.

## Usage

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
```

Custom semantic colors:
```tsx
<span className="text-success">Passed</span>
<span className="text-warning">Pending</span>
<span className="text-info">Info</span>
```
