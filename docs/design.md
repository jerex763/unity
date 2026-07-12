# Design Direction

Extracted from the UI requirements doc. This is the shared visual language for all frontend PRs — deviate deliberately, not accidentally.

## Ethos

Warm, pastoral, faith-centered. "Data is not statistics — it represents people loved by God." Calm over flashy; growth and relationship as the core metaphor.

## Tokens (starting values — refine in issue #6, keep as CSS custom properties)

The docs specify direction ("greens, soft beige, light cream") but no hex values. Proposed starting palette:

```css
:root {
  --color-primary: #2F6B4F;      /* deep leaf green — actions, links */
  --color-primary-soft: #E8F0EA; /* green tint — selected states, chips */
  --color-surface: #FBF8F1;      /* light cream — app background */
  --color-card: #FFFFFF;         /* cards */
  --color-beige: #F0E9DC;        /* soft beige — section accents */
  --color-text: #26302B;
  --color-text-muted: #5D6B63;
  --color-urgent: #B4552D;       /* care urgency, warm not alarming */

  --radius-card: 16px;
  --radius-chip: 999px;
  --shadow-card: 0 1px 3px rgb(0 0 0 / 0.06);  /* minimal shadows per docs */

  --font-sans: "Inter", system-ui, sans-serif;
}
```

All colors must hold **4.5:1 contrast** against their background (docs requirement). Check with a contrast tool before merging.

## Component inventory (per UI doc)

- **Cards** — rounded (16px), minimal shadow: events, groups, follow-up entries, insight cards
- **Chips** — pill-shaped: next-step labels, rationale tags ("Missed 3 events"), filters
- **Tabs** — person profile sections (Overview / Timeline / Groups / Care)
- **Kanban board** — care cases (New → In Progress → Waiting → Closed), drag between columns
- **Lists** — directory, follow-up queue, registrations; photo-led rows
- **Modals** — guided flows (follow-up contact logging), confirmations
- **FAITH ring** — five-segment ring around avatar (post-MVP; don't build now, but leave avatar component room for it)

## Rules

- Mobile-first: primary users are leaders on phones at church
- Externalize every UI string (i18next) — multilingual is a stated requirement, translations come later
- Semantic HTML, keyboard navigable, visible focus states
- No dark-pattern urgency; `--color-urgent` is for care crises only
