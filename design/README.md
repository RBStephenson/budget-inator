# Handoff: Budget-inator UI Redesign

## Overview
A redesign of the existing Budget-inator React frontend (pay-schedule/bill-tracking app), focused on: bigger structural rethink (sidebar navigation instead of top nav), larger touch targets, status shown via icon + text label (not color alone), an inline quick-add for bills (replacing the always-modal "Add Bill" flow), and a dark mode toggle. Scope: Dashboard, Bills, Settings, Help, the full Add/Edit Bill form, and confirm dialogs.

## About the Design Files
The bundled file (`Budget-inator.dc.html`) is a **design reference** built as a single self-contained interactive HTML prototype — it is NOT production code to copy directly. It demonstrates layout, states, copy, and interaction intent (page switching, opening the slide-over form, the deactivate-confirm dialog, and the dark-mode toggle all work by clicking around in it).

The task is to **recreate this design in the actual Budget-inator codebase** (React + TypeScript, Vite) using its existing patterns: component structure in `src/components/`, hooks in `src/hooks/`, the API client in `src/api/`, and the existing `App.css` custom-property system (`--color-*`, `--radius-*`, `--shadow-*` in `:root`). Do not introduce a second styling system — extend the existing CSS variables with the new dark-mode tokens listed below.

## Fidelity
**High-fidelity.** Colors, spacing, type sizes, and copy are final. Treat pixel values and hex codes below as authoritative; the prototype's inline styles are the source of truth (open the HTML file and inspect any element for exact values).

## Screens / Views

### 1. Shell / Navigation (all pages)
- Layout: two-column CSS grid, `220px` sidebar + flexible content area, `min-height:100vh`.
- Sidebar: dark navy (`#0f1b33` light mode and dark mode — sidebar itself doesn't change with theme), `24px 16px` padding, vertical flex, `4px` gap.
  - Logo/wordmark: "Budget-inator", white, 800 weight, 18px.
  - Nav buttons: 🏠 Dashboard, 🧾 Bills, ⚙️ Settings, ❓ Help. Each `min-height:48px`, full width, `border-radius:10px`, `14px` font, 700 weight when active. Active state: background `#1e3a8a`, text white. Inactive: transparent background, `#cbd5e1` text.
  - Bottom of sidebar (pinned via `margin-top:auto`): dark-mode toggle button (🌙 Dark mode / ☀ Light mode, `min-height:44px`), then "Next payday" mini-stat.
- Replaces the current top horizontal header/nav (`.app-header`, `.app-nav` in the existing App.css) entirely.

### 2. Dashboard
- Header row: "Current period" eyebrow (12px, 700, uppercase, blue `#2563eb`) + `Jul 10 – Jul 24` H1 (26px), right-aligned "⚠ Available running low" pill (amber bg/text) when balance is low.
- Stat card row: 4-column grid, `14px` gap. Cards: Available, Bills due, Flagged late (amber/orange variant), Paid so far. Each `12px` radius, `16px` padding.
- Inline quick-add bar: dashed blue border (`1.5px dashed #3b82f6`), light blue background, contains Name/Amount/Category inputs + Add button + a text link "Open full form →" that opens the full slide-over (see Screen 5) for recurrence/sinking-fund/grace-period fields.
- Bill list: vertical stack, `10px` gap. Each row: `5px` solid left border colored by status (green=paid, orange=late/can't-pay-on-time, slate=due-soon, gray=skipped), icon (✓ / ⚠ / ◷ / —), bold name + muted category, a bold status word underneath the name (PAID / CAN'T PAY ON TIME / DUE SOON / SKIPPED), amount right-aligned, and action buttons (`44px` min-height). This replaces `BillRow.tsx`'s current small icon-only/color-only status badges.
- **Behavior fix**: editing an actual amount happens inline within the row (no modal, no scroll-to-top) — this addresses the reported bug where entering an actual amount jumped the page back to the top.

### 3. Bills page
- Same page-hero pattern (eyebrow + H1) as Dashboard.
- Inline quick-add bar (same component pattern as Dashboard, with added Recurrence + Due day fields) replaces opening `BillFormModal` for the common "just add a normal monthly bill" case. The existing modal-based full form is kept, accessible via "Open full form →" for sinking funds, grace periods, variable amounts.
- Search input + category filter + sort buttons (same as current `BillTable.tsx` controls, just larger targets: `44px` min-height).
- Bill rows: same left-border-accent pattern as Dashboard's bill rows, with Edit / Deactivate buttons (`44px`, ghost style / red-text style).
- Footer total row: `2px` top border, bold total.

### 4. Settings page
- Two stacked cards (not side-by-side columns like the current two-column `.settings-page__content` grid — full width, stacked, more breathing room):
  - "Pay schedule" card: 2-column form grid, `48px` inputs, labelled with inline hint text (e.g. "First paycheck date — anchors your periods").
  - "Data management" card: Export / Import rows (`48px` buttons) + a visually distinct danger-zone row for Delete All (🗑 icon, red 2px border, red-tinted background, red button) — not just red text on a white card like the current `.settings-data__item--danger`.

### 5. Full Add/Edit Bill form (slide-over panel)
- Replaces the small centered `.modal` (max-width 560px) used today. Instead: a **520px-wide slide-over panel** anchored to the right edge, full height, with a dimmed backdrop over the rest of the app — better for a form with this many fields.
- Grouped into 3 numbered sections: "1 · Basics" (Name, Amount, Category), "2 · Schedule" (Recurrence as pill/segmented buttons instead of a `<select>`, then only the relevant date field — e.g. "Next due date" for non-monthly, "Due day 1–31" for monthly — never both), "3 · Options" (Variable amount, Sinking fund, each as a checkbox row with helper text).
- Footer: Cancel (ghost) + primary Add/Save button, both `48px`.

### 6. Confirm dialogs
- Standard confirm (e.g. deactivate bill): icon + title + description, Cancel (ghost) + solid dark primary action, `48px` buttons.
- Destructive confirm (delete all data): red top border accent, ⚠ icon, and a **type "DELETE" to confirm** text input that gates the destructive button (disabled until typed) — the current app has no such safeguard for "Delete all data."
- Multi-item confirm (rebalance preview): same shell, lists each proposed move with a `↔` icon, before/after amounts, and reason text, then "Apply N moves".

## Interactions & Behavior
- Sidebar nav switches the visible page; no full page reload (matches current SPA router behavior in `App.tsx` / `router.ts` — reuse that, just move the nav markup into the sidebar).
- Dark mode toggle flips a `dark` boolean; persisted to `localStorage` (key: `budgetinator-dark`, values `"1"`/`"0"`) and re-applied on load.
- "Open full form →" links open the slide-over panel; clicking the backdrop or the ✕ closes it.
- Deactivate button opens the standard confirm dialog.
- All action buttons/inputs: minimum 44px touch target (48px for primary/form actions), per accessibility requirement.
- Status is always icon + text label + colored left border — never color-only — for colorblind/grayscale/screen-reader users.

## State Management
Mirrors what the current codebase already tracks per-component (`useSchedule`, `useBills`, per-row local state for editing amounts/dates); nothing new is required except:
- A `dark` boolean (persisted to localStorage) — new, app-wide.
- Current page/route — already handled by `App.tsx`'s `getPage()`/`popstate` pattern; just move the nav UI, not the logic.

## Design Tokens

### Light mode (extends existing `:root` vars in `App.css`)
- `--bg0` (app background): `#eef1f5`
- `--bg1` (card/surface): `#ffffff`
- `--bg1alt` (stat-card tint): `#f8fafc`
- `--border1`: `#e5e7eb`  ·  `--border2`: `#f3f4f6`
- `--text1` (primary text): `#111827`  ·  `--text2` (muted): `#6b7280`  ·  `--text3` (lightest muted): `#9ca3af`
- Status tints: warn (amber) bg `#fef3c7` / text `#92400e`; orange/late bg `#fff7ed` / border `#fdba74` / text `#9a3412`; green accent `#16a34a`/`#166534`; blue accent `#2563eb`/`#1d4ed8`.

### Dark mode (new)
- `--bg0`: `#0b1220`  ·  `--bg1`: `#111827`  ·  `--bg1alt`: `#0d1420`
- `--border1` / `--border2`: `#1f2937`
- `--text1`: `#f1f5f9`  ·  `--text2`: `#94a3b8`  ·  `--text3`: `#64748b`
- warn bg `#3f2d0a` / text `#fbbf24`; orange bg `#2a1207` / border `#7c2d12` / text `#fdba74`; green accent `#22c55e`; blue accent `#3b82f6`/`#60a5fa`; danger bg `#2a0f0f`.
- Sidebar stays `#0f1b33` in both modes (it's already dark).

### Typography
- Font: Inter (400/500/600/700/800), falling back to the existing system stack in `App.css`.
- Sizes in use: 26px (page H1), 18–19px (card/modal titles), 15px (body/row text), 13–14px (buttons/labels/meta), 12px (eyebrows/uppercase labels).

### Radii & spacing
- Card radius: `12–16px`. Button/input radius: `8–10px`. Pill radius: `999px`.
- Row gap rhythm: `10px` between list rows, `14–24px` for section spacing.

## Assets
No new image assets — emoji are used as icons (🏠 🧾 ⚙️ ❓ ✓ ⚠ ◷ — 🗑 ↔ 🌙 ☀). If the target codebase prefers an icon set (e.g. Lucide/Heroicons, whatever is already a dependency) swap these 1:1 for icon components of equivalent meaning.

## Files
- `Budget-inator.dc.html` — the interactive design reference. Open it in a browser to click through Dashboard/Bills/Settings/Help, the dark-mode toggle, the Add Bill slide-over, and the deactivate confirm dialog. View source / inspect elements for exact inline style values (all styling is inline, so every value is directly visible on the element).
- `screenshots/01-dashboard.png` — Dashboard, light mode
- `screenshots/02-bills.png` — Bills page, light mode
- `screenshots/03-settings.png` — Settings page, light mode
- `screenshots/04-help.png` — Help page, light mode
- `screenshots/05-dashboard-dark.png` — Dashboard, dark mode
