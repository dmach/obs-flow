# OBS Flow — Design System

> GitHub product look and feel (Primer), built on stock Pico CSS v2, driven by htmx, light **and** dark.

OBS Flow should feel like working on github.com: a quiet, neutral canvas, 14px system type, 6px corners,
hairline borders instead of shadows, blue for links and focus, green only for the main action of a form
or dialog, and colored pill labels for states (open / merged / closed).

The reference is the GitHub *application* UI (pull request list, PR page, repository settings), not the
github.com marketing homepage. No glass, glows, gradients or display typography.

## Constraints

- **No Node.js.** No npm, no bundler, no PostCSS/Tailwind build. CSS and JS are hand-written static files.
- **Pico CSS v2** provides the base styling. We only override Pico's `--pico-*` variables and add a few
  components in `static/css/flow.css`.
- **htmx** does all interactivity (server-rendered partials swapped into the page). JavaScript is the
  exception (`static/js/flow.js`), never inline `onclick` or `<script>` blocks in templates.
- **Third-party assets are vendored** into `static/vendor/` (Pico, htmx) with a pinned version, rather
  than loaded from a CDN.
- **No web fonts.** GitHub's product UI uses the system font stack; so do we.
- **No hard-coded colors in templates.** No inline `style="..."`. Everything goes through tokens.

## Themes

Three modes, matching the existing user preference (`auto` / `light` / `dark`):

| Preference | `<html>` attribute | Result |
|---|---|---|
| auto | *(none)* | Follows the OS `prefers-color-scheme` |
| light | `data-theme="light"` | Always light |
| dark | `data-theme="dark"` | Always dark |

Every color token is declared **once** with CSS `light-dark(<light>, <dark>)`. The browser chooses the
value from the element's `color-scheme`, which we set from `data-theme`. No duplicated light/dark blocks,
no JavaScript, no build step. (`light-dark()` is Baseline 2024: Firefox 120+, Chrome 123+, Safari 17.5+.)

## Color tokens

Values follow GitHub Primer's "light default" and "dark default" themes.

### Backgrounds

| Token | Light | Dark | Use |
|---|---|---|---|
| `--gh-bg-default` | `#ffffff` | `#0d1117` | Page canvas, table rows, cards, inputs |
| `--gh-bg-subtle` | `#f6f8fa` | `#151b23` | Table / box headers, filter summary, row hover |
| `--gh-bg-inset` | `#f6f8fa` | `#010409` | App header bar, `<pre>` blocks |
| `--gh-bg-overlay` | `#ffffff` | `#151b23` | Dialogs, dropdowns, toasts |
| `--gh-bg-neutral-muted` | `#818b981f` | `#656c7633` | Counters, inline `<code>`, dropdown item hover |
| `--gh-bg-accent-muted` | `#ddf4ff` | `#388bfd1a` | Selected rows, info flash, text selection |
| `--gh-bg-success-muted` | `#dafbe1` | `#2ea04326` | Success flash |
| `--gh-bg-attention-muted` | `#fff8c5` | `#bb800926` | Warning flash |
| `--gh-bg-danger-muted` | `#ffebe9` | `#f8514926` | Error flash |

### Foreground

| Token | Light | Dark | Use |
|---|---|---|---|
| `--gh-fg-default` | `#1f2328` | `#f0f6fc` | Body text, headings |
| `--gh-fg-muted` | `#59636e` | `#9198a1` | Secondary text, table headers, metadata, footer |
| `--gh-fg-on-emphasis` | `#ffffff` | `#ffffff` | Text on filled buttons and state labels |
| `--gh-fg-accent` | `#0969da` | `#4493f8` | Links, focus ring, active input border |
| `--gh-fg-success` | `#1a7f37` | `#3fb950` | Positive text ("yes", accepted) |
| `--gh-fg-attention` | `#9a6700` | `#d29922` | Pending / waiting text |
| `--gh-fg-danger` | `#d1242f` | `#f85149` | Errors, rejected, destructive button text |
| `--gh-fg-done` | `#8250df` | `#ab7df8` | Merged / completed text |

### Emphasis (filled state labels, primary button)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--gh-success-emphasis` | `#1f883d` | `#238636` | Primary button, "Open" label |
| `--gh-done-emphasis` | `#8250df` | `#8957e5` | "Merged" label |
| `--gh-danger-emphasis` | `#cf222e` | `#da3633` | "Closed"/"Failed" label, danger button hover |
| `--gh-attention-emphasis` | `#9a6700` | `#9e6a03` | "Pending release" label |
| `--gh-accent-emphasis` | `#0969da` | `#1f6feb` | Checked checkboxes and radios |
| `--gh-neutral-emphasis` | `#59636e` | `#656c76` | "Draft"/"Collecting" label |

### Borders

| Token | Light | Dark | Use |
|---|---|---|---|
| `--gh-border-default` | `#d1d9e0` | `#3d444d` | Box/table outline, inputs, buttons, dialogs |
| `--gh-border-muted` | `#d1d9e0b3` | `#3d444db3` | Row dividers, sidebar section dividers |
| `--gh-border-active` | `#fd8c73` | `#f78166` | Underline of the current top-nav item |

### Buttons

| Token | Light | Dark |
|---|---|---|
| `--gh-btn-bg` | `#f6f8fa` | `#212830` |
| `--gh-btn-hover-bg` | `#eff2f5` | `#262c36` |
| `--gh-btn-border` | `#d1d9e0` | `#3d444d` |
| `--gh-btn-primary-bg` | `#1f883d` | `#238636` |
| `--gh-btn-primary-hover-bg` | `#1c8139` | `#29903b` |
| `--gh-btn-primary-border` | `#1f232826` | `#ffffff1a` |
| `--gh-btn-danger-hover-bg` | `#cf222e` | `#b62324` |

### Shadows and backdrop

Shadows only appear on things that float above the page (dialogs, dropdowns, toasts). Cards, tables
and buttons get a border, not a shadow.

| Token | Light | Dark |
|---|---|---|
| `--gh-shadow-color` | `#25292e1f` | `#010409` |
| `--gh-backdrop` | `#1f232866` | `#010409b3` |

## Typography

| Token | Value |
|---|---|
| `--gh-font-sans` | `-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji"` |
| `--gh-font-mono` | `ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace` |

The base size is the user's font-size preference (12–20px, **default 14px**, like GitHub). It is
applied as `--pico-font-size` on `<html>`, so every size below is in `rem`. That way the whole UI,
controls included, scales with the preference.

| Role | Element | Size | Weight | Line height |
|---|---|---|---|---|
| Page title | `h1` (one per page) | 2rem | 400 | 1.25 |
| Section heading | `h2` | 1.5rem | 600 | 1.25 |
| Subsection / dialog title | `h3` | 1.25rem (1rem inside dialogs) | 600 | 1.25 |
| Box heading | `h4` | 1rem | 600 | 1.5 |
| Sidebar heading | `.sidebar-section h4` | 0.857rem | 600, muted, **not** uppercase | 1.5 |
| Body | `p`, `td` | 1rem | 400 | 1.5 |
| Small / metadata | `small`, help text, footer | 0.857rem | 400 | 1.5 |
| Code, SHA, branch | `code` | 0.857rem mono | 400 | 1.5 |

The page title is followed by a muted identifier, GitHub-style:
`<h1>Fix build on s390x <span class="muted">#123</span></h1>`.

> Migration: templates currently use `h2` for page titles and `h3` for sections. Move them one level up.

## Spacing, shape, layout

- **Spacing base:** 4px. Use 4 / 8 / 12 / 16 / 24 / 32 / 40px (in rem at 14px base: 0.286 / 0.571 /
  0.857 / 1.143 / 1.714 / 2.286 / 2.857). Pico's `--pico-spacing` stays `1rem`.
- **Radius:** `6px` for buttons, inputs, boxes, tables, cards, code, flashes, toasts. `12px` for
  dialogs. `2em` (pill) for state labels, review labels and counters. Nothing else.
- **Borders:** always 1px.
- **Container:** fluid, max-width `1280px`, horizontal padding `1rem`.
- **Detail pages:** main column + sidebar, `3fr 1fr`, gap `1.5rem`. A single column below `768px`.
- **Breakpoint:** a single one at `768px` (Primer `md`).

## Components

### App header

Two rows, like a GitHub repository header, on a `--gh-bg-inset` background with a 1px
`--gh-border-default` bottom border. No SUSE green, and no vertical padding on the header itself.

- **Top row (`.app-header-top`):** min height 3.5rem. On the left, the brand (`.app-brand`): the logo
  (2rem) plus "OBS Flow" at 1.143rem/600 `--gh-fg-default`. On the right, the account nav: the user
  dropdown (Preferences, Tokens, Bookmarks, Logout), or "Log In".
- **Tab row (`nav.app-tabs`):** the section links Git Mappings, Pull Requests, Staging Batches.
  1rem/400 `--gh-fg-default`, padding `0.375rem 0.5rem`, radius 6px, hover background
  `--gh-bg-neutral-muted`.
- **Current tab:** `aria-current="page"`, weight 600, with a 2px `--gh-border-active` bar along the
  header's bottom edge (GitHub "UnderlineNav").
- **Small screens:** the same layout. The tab row scrolls horizontally if it doesn't fit.

### Logo

An isometric cube (a built package) wrapped by a green flow band that leaves it as an upward arrow
(the workflow toward release). It was made in Recraft and has two colours:

| Part | Light | Dark |
|---|---|---|
| Base (`.logo-base`) | `#13372c` | `#f0f6fc` |
| Accent (`.logo-accent`) | `#32f773` | `#32f773` |

- **In the page:** inline from `templates/partials/logo.svg`. Colours come from `.app-logo` rules in
  `flow.css` (`light-dark()`), so it follows an explicit light/dark preference too. Path order
  matters: the accent paths must stay after the first base path.
- **Favicon:** `static/img/logo.svg`, the same paths with the colours embedded and switched by
  `prefers-color-scheme`.
- Don't recolour it, add effects, or put it on a filled background. The minimum size is 16px.

### Buttons

Height ≈ 32px (`--pico-form-element-spacing-vertical: 0.3125rem`, horizontal `0.75rem`), 1rem/500,
radius 6px, 1px border, sized to their label (never full width).

| Variant | Markup | Rest | Hover |
|---|---|---|---|
| Default | `class="secondary"` (also `secondary outline`, `contrast`) | `--gh-btn-bg`, `--gh-btn-border`, text `--gh-fg-default` | `--gh-btn-hover-bg` |
| Primary | `<button>` / `class="primary"` | `--gh-btn-primary-bg`, text white | `--gh-btn-primary-hover-bg` |
| Danger | `class="danger"` | Default background, text `--gh-fg-danger` | `--gh-btn-danger-hover-bg`, text white |
| Invisible | `class="invisible"` | Transparent, no border, text `--gh-fg-accent` | `--gh-bg-neutral-muted` |

Rules:
- At most **one primary** button per form, dialog or toolbar. It is the action that moves things
  forward (Save, Stage, Next, Log In).
- **Destructive** actions (Delete, Revoke) use `danger`, never primary.
- **Cancel** is a default button.
- In dialogs and forms the buttons are right-aligned, with the primary one last.
- Disabled buttons use 50% opacity and `cursor: not-allowed`.

### Links

- **Normal links:** `--gh-fg-accent`, no underline, underline on hover.
- **Muted links:** `a.secondary` (footer, breadcrumbs, table metadata) use `--gh-fg-muted`, turning
  accent on hover.
- **Identifiers:** `owner/repo#123` and SHAs are links in default text color, accent on hover.

### Box and data tables

The main building block: `<table class="data-table">`. It looks like a GitHub issue/PR list:

- **Outline:** 1px `--gh-border-default`, radius 6px, `overflow: hidden`.
- **`thead`:** `--gh-bg-subtle` background, 1rem/600 `--gh-fg-muted` text. Sort links are muted, accent
  on hover. The current direction shows as `▲` / `▼`.
- **Rows:** no zebra striping. 1px `--gh-border-muted` dividers, cell padding `0.5rem 1rem`, hover
  `--gh-bg-subtle`.
- **Checked rows:** `tr:has(input[type=checkbox]:checked)` gets `--gh-bg-accent-muted`.
- **Narrow columns:** checkbox column 40px, centered.
- **Small screens (< 768px):** rows become stacked cards (current behavior). Each `td` shows its
  `data-label` as a muted bold prefix.
- **Empty table:** show a blank slate instead (see below).

`article` (Pico card) is a Box too: a 1px border (drawn as `box-shadow: 0 0 0 1px`), radius 6px, no
drop shadow, and `--gh-bg-subtle` for its `header` and `footer`.

### State labels (filled pill)

`<span class="state" data-state="{{ obj.state }}">{{ obj.get_state_display }}</span>`

1rem/500, padding `0.25rem 0.75rem`, radius 2em, white text, background by state:

| Model | State value | Color |
|---|---|---|
| PullRequest | `open` | `--gh-success-emphasis` |
| PullRequest | `merged` | `--gh-done-emphasis` |
| PullRequest | `closed` | `--gh-danger-emphasis` |
| PullRequest | draft (`is_draft`) | `--gh-neutral-emphasis`, text "Draft" |
| StagingBatch | `collecting` | `--gh-neutral-emphasis` |
| StagingBatch | `in-progress/open` | `--gh-success-emphasis` |
| StagingBatch | `pending-release` | `--gh-attention-emphasis` |
| StagingBatch | `merged/completed` | `--gh-done-emphasis` |
| StagingBatch | `failed` | `--gh-danger-emphasis` |

Use the `data-state` attribute, not a generated class name. State values contain `/`, and attribute
selectors (`[data-state="in-progress/open"]`) handle that cleanly.

### Review labels (outlined pill)

`<span class="label" data-state="{{ review.state }}">{{ review.get_state_display }}</span>`

0.857rem/500, line height 1.5, padding `0 0.5rem`, radius 2em, 1px border in the text color,
transparent background:

| State | Color |
|---|---|
| `accepted` | `--gh-fg-success` |
| `rejected` | `--gh-fg-danger` |
| `pending` | `--gh-fg-attention` |
| `needinfo` | `--gh-fg-accent` |
| `waiting`, `overridden` | `--gh-fg-muted` |

**Mergeable** shows as text, not a label: "yes" in `--gh-fg-success`, "no" in `--gh-fg-danger`,
"unknown" in `--gh-fg-muted`.

Color never carries meaning alone. The label text is always present.

### Counter

`<span class="counter">{{ total_count }}</span>` next to page titles, tabs and box headings.

0.857rem/500, min-width 1.5em, padding `0 0.4rem`, radius 2em, `--gh-bg-neutral-muted` background,
`--gh-fg-default` text, centered. (Replaces `<small>` and `.badge` after headings.)

### Forms

- **Labels:** 1rem/600 `--gh-fg-default`, `0.25rem` gap below. `legend` looks the same.
- **Inputs, selects:** `--gh-bg-default`, 1px `--gh-border-default`, radius 6px, same height as
  buttons. Focus: border `--gh-fg-accent` plus a 2px accent ring.
- **Placeholder:** `--gh-fg-muted`.
- **Help text:** `<small>` below the field, 0.857rem muted.
- **Errors:** `aria-invalid="true"` on the input (red border via Pico), then
  `<small class="error">message</small>` in `--gh-fg-danger`. No inline styles.
- **Grouped input + button:** Pico `fieldset[role=group]` (e.g. "Generate token").

### Filter panel

A Box built from `<details class="filter-panel">`. The `summary` is a `--gh-bg-subtle` header row,
1rem/600, with a bottom border when open. Body padding `1rem`. Actions are right-aligned: "Reset"
(default) and "Apply Filter" (primary). It is open by default when a filter is active.

### Dialog

Pico `<dialog open>` with an `article` inside, inserted into `#modal-container` by htmx.

- **Panel:** `--gh-bg-overlay`, radius 12px, overlay shadow, max-width 40rem.
- **Backdrop:** `--gh-backdrop`, **no blur**.
- **Header:** `--gh-bg-default`, title `h3` at 1rem/600, bottom border `--gh-border-muted`.
- **Footer:** top border `--gh-border-muted`, buttons right-aligned with `0.5rem` gap, primary or danger
  last.
- **Close:** with Escape and Cancel (the existing `method="dialog"` + htmx pattern).

### Dropdown

Pico `details.dropdown`.

- **Menu:** `--gh-bg-overlay`, 1px `--gh-border-default`, radius 12px, overlay shadow, `0.5rem`
  padding.
- **Items:** 1rem/400, padding `0.375rem 0.5rem`, radius 6px, hover `--gh-bg-neutral-muted`.

### Flash (inline notice)

`<div class="flash flash-success|flash-warning|flash-danger|flash-info">…</div>`, for page-level
messages such as "Token generated, copy it now".

1px border, radius 6px, padding `1rem`, text `--gh-fg-default`. Colors per variant:

| Variant | Background | Border |
|---|---|---|
| info | `--gh-bg-accent-muted` | `--gh-fg-accent` at 40% |
| success | `--gh-bg-success-muted` | `--gh-fg-success` at 40% |
| warning | `--gh-bg-attention-muted` | `--gh-fg-attention` at 40% |
| danger | `--gh-bg-danger-muted` | `--gh-fg-danger` at 40% |

### Toast

Server-rendered from Django messages, shown bottom-right, auto-hidden by CSS animation.

`--gh-bg-overlay`, 1px `--gh-border-default`, radius 6px, overlay shadow, padding `0.75rem 1rem`, 1rem
text. There is a 4px left border in `--gh-fg-success` / `--gh-fg-danger` / `--gh-fg-attention`.

### Blank slate (empty states)

Replaces `<p class="muted">No … found.</p>`.

A Box with centered content and `2rem` padding. Heading 1.25rem/600, description `--gh-fg-muted`, and
an optional single action button.

### Sidebar (detail pages)

Plain column, **no card around it**, matching the GitHub PR sidebar.

- **Sections:** each `.sidebar-section` ends with a 1px `--gh-border-muted` bottom border and
  `0.75rem` padding.
- **Headings:** 0.857rem/600 muted.
- **Values:** 1rem.
- **Inline editing:** an `Edit` invisible button next to the heading swaps in a small form via htmx.

### Breadcrumb

Pico `nav[aria-label=breadcrumb]` with `/` as divider (`--pico-nav-breadcrumb-divider`). Links are
muted; the current item is `--gh-fg-default`, weight 600.

### Pagination

Shared partial `partials/pagination.html` (include it with the `page_obj` in context). It renders a
centered row: First / Previous, "Page X of Y", Next / Last. Items have padding `0.25rem 0.625rem` and
radius 6px. Links show a `--gh-border-default` border on hover.

- **Current page:** the plain text `<span aria-current="page">Page X of Y</span>` in
  `--gh-fg-default`. There are no numbered page links.
- **Disabled First/Previous/Next/Last:** `<span aria-disabled="true">` in `--gh-fg-muted`, no hover.

### Code, SHAs, branches

- **Inline `code`:** `--gh-font-mono` 0.857rem, `--gh-bg-neutral-muted` background, padding
  `0.2em 0.4em`, radius 6px.
- **SHAs:** 8 characters, fingerprints 12.
- **`pre`:** `--gh-bg-inset`, 1px border, radius 6px, padding `1rem`, horizontal scroll.

### Footer

Top border `--gh-border-muted`, padding `2.5rem 0`, centered, 0.857rem `--gh-fg-muted`. Links are muted
and turn accent on hover. Items are separated by `·`.

### Home page

GitHub dashboard tone, not a marketing hero: page title, a one-line muted description, and two buttons
("View Pull Requests" primary, "View Staging Batches" default). Below them, there can optionally be
boxes with recent items. No gradients, illustrations or oversized type.

## htmx states

- **Loading:** htmx adds `htmx-request` to the element issuing the request. Style it in CSS, with no
  JavaScript:
  - `form.htmx-request [type=submit]`, `button.htmx-request`: 50% opacity, `pointer-events: none`,
    `cursor: progress`.
  - `.htmx-indicator`: hidden (`opacity: 0`), shown when it or an ancestor has `.htmx-request`. Use
    for small "Saving…" text or a spinner next to the trigger.
- **Swapped content:** fades in with `opacity` over 150ms. No layout-shifting animations.
- **Errors:** come back as server-rendered partials (error dialog or `.flash-danger`), never as
  `alert()`.
- **CSRF:** sent via `hx-headers:inherited` on `<body>` (already in place).

## Motion

- **Timing:** `--pico-transition: 80ms cubic-bezier(0.33, 1, 0.68, 1)` for hover/focus. 150–300ms for
  dialogs, toasts and swaps.
- **What to animate:** only `opacity` and `transform`. Color/background changes on hover are instant or
  use the 80ms transition.
- **Reduced motion:** `prefers-reduced-motion: reduce` disables every animation.

## Accessibility

- **Contrast:** all text/background pairs above meet WCAG AA in both themes (Primer values). Don't
  invent new color pairs.
- **Focus:** always visible, a 2px `--gh-fg-accent` ring. Never `outline: none` without a replacement.
- **Color:** state is never shown by color alone. Labels carry text, and table cells repeat
  `data-label` on mobile.
- **Dialogs:** have a heading, close with Escape, and the primary action is reachable by keyboard.
- **Current page:** the active navigation item has `aria-current="page"`.

## Do / Don't

**Do**
- Keep the base at 14px system font, 6px corners and 1px borders. That is most of the GitHub feel.
- Use blue (`--gh-fg-accent`) for links, focus and selection; green only for the one primary button.
- Use filled pills for object state (PR, batch), outlined pills for review state, counters for totals.
- Build lists as bordered tables with a subtle header row and hover, like the GitHub PR list.
- Express every color through a `--gh-*` token so both themes work automatically.

**Don't**
- No glassmorphism, `backdrop-filter`, gradients, glows or illustrations.
- No zebra striping, no card drop shadows, no shadows on buttons beyond Primer's 1px resting shadow.
- Don't make links green or buttons blue.
- Don't use a primary (green) button for destructive actions.
- No inline `style=""`, no hex values in templates, no class names built from data (`toast-{{ x }}` is
  fine only because the values are a closed set defined in CSS).
- No Node-based tooling, CDN-loaded runtime assets or web fonts.

## Implementation (`static/css/flow.css`)

Load order: `vendor/pico/pico.min.css`, then `css/flow.css`. Everything below is plain CSS.

### 1. Theme selection

```css
/* Pico already sets color-scheme per theme; these rules make it explicit and
   are what light-dark() below resolves against. */
:root:not([data-theme]) { color-scheme: light dark; }
[data-theme="light"]    { color-scheme: light; }
[data-theme="dark"]     { color-scheme: dark; }
```

### 2. Tokens (one block, both themes)

```css
:root {
    --gh-font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
    --gh-font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;

    --gh-bg-default:          light-dark(#ffffff, #0d1117);
    --gh-bg-subtle:           light-dark(#f6f8fa, #151b23);
    --gh-bg-inset:            light-dark(#f6f8fa, #010409);
    --gh-bg-overlay:          light-dark(#ffffff, #151b23);
    --gh-bg-neutral-muted:    light-dark(#818b981f, #656c7633);
    --gh-bg-accent-muted:     light-dark(#ddf4ff, #388bfd1a);
    --gh-bg-success-muted:    light-dark(#dafbe1, #2ea04326);
    --gh-bg-attention-muted:  light-dark(#fff8c5, #bb800926);
    --gh-bg-danger-muted:     light-dark(#ffebe9, #f8514926);

    --gh-fg-default:          light-dark(#1f2328, #f0f6fc);
    --gh-fg-muted:            light-dark(#59636e, #9198a1);
    --gh-fg-on-emphasis:      #ffffff;
    --gh-fg-accent:           light-dark(#0969da, #4493f8);
    --gh-fg-success:          light-dark(#1a7f37, #3fb950);
    --gh-fg-attention:        light-dark(#9a6700, #d29922);
    --gh-fg-danger:           light-dark(#d1242f, #f85149);
    --gh-fg-done:             light-dark(#8250df, #ab7df8);

    --gh-success-emphasis:    light-dark(#1f883d, #238636);
    --gh-done-emphasis:       light-dark(#8250df, #8957e5);
    --gh-danger-emphasis:     light-dark(#cf222e, #da3633);
    --gh-attention-emphasis:  light-dark(#9a6700, #9e6a03);
    --gh-accent-emphasis:     light-dark(#0969da, #1f6feb);
    --gh-neutral-emphasis:    light-dark(#59636e, #656c76);

    --gh-border-default:      light-dark(#d1d9e0, #3d444d);
    --gh-border-muted:        light-dark(#d1d9e0b3, #3d444db3);
    --gh-border-active:       light-dark(#fd8c73, #f78166);

    --gh-btn-bg:              light-dark(#f6f8fa, #212830);
    --gh-btn-hover-bg:        light-dark(#eff2f5, #262c36);
    --gh-btn-border:          light-dark(#d1d9e0, #3d444d);
    --gh-btn-primary-bg:      light-dark(#1f883d, #238636);
    --gh-btn-primary-hover-bg: light-dark(#1c8139, #29903b);
    --gh-btn-primary-border:  light-dark(#1f232826, #ffffff1a);
    --gh-btn-danger-hover-bg: light-dark(#cf222e, #b62324);

    --gh-shadow-color:        light-dark(#25292e1f, #010409);
    --gh-shadow-overlay:      0 0 0 1px var(--gh-border-default), 0 8px 24px 0 var(--gh-shadow-color);
    --gh-shadow-resting:      0 1px 0 0 light-dark(#1f23280a, #00000000);
    --gh-backdrop:            light-dark(#1f232866, #010409b3);
}
```

### 3. Map tokens onto Pico

Pico declares its colors on `:root:not([data-theme=dark])`, `[data-theme=light]` and
`:root:not([data-theme])`, all with specificity (0,2,0) or lower. The selector below has (0,2,0), comes
later, and so wins in every mode.

```css
:root[data-theme],
:root:not([data-theme]) {
    --pico-font-family-sans-serif: var(--gh-font-sans);
    --pico-font-family-monospace: var(--gh-font-mono);
    --pico-font-family: var(--pico-font-family-sans-serif);
    --pico-line-height: 1.5;
    --pico-border-radius: 6px;
    --pico-border-width: 1px;
    --pico-outline-width: 2px;
    --pico-transition: 80ms cubic-bezier(0.33, 1, 0.68, 1);
    --pico-form-element-spacing-vertical: 0.3125rem;
    --pico-form-element-spacing-horizontal: 0.75rem;
    --pico-nav-breadcrumb-divider: "/";

    --pico-background-color: var(--gh-bg-default);
    --pico-color: var(--gh-fg-default);
    --pico-h1-color: var(--gh-fg-default);
    --pico-h2-color: var(--gh-fg-default);
    --pico-h3-color: var(--gh-fg-default);
    --pico-h4-color: var(--gh-fg-default);
    --pico-h5-color: var(--gh-fg-default);
    --pico-h6-color: var(--gh-fg-default);
    --pico-muted-color: var(--gh-fg-muted);
    --pico-muted-border-color: var(--gh-border-muted);
    --pico-text-selection-color: var(--gh-bg-accent-muted);

    /* Links and focus are blue; filled (primary) buttons are green. */
    --pico-primary: var(--gh-fg-accent);
    --pico-primary-hover: var(--gh-fg-accent);
    --pico-primary-underline: transparent;
    --pico-primary-hover-underline: var(--gh-fg-accent);
    --pico-primary-focus: var(--gh-fg-accent);
    --pico-primary-background: var(--gh-btn-primary-bg);
    --pico-primary-border: var(--gh-btn-primary-border);
    --pico-primary-hover-background: var(--gh-btn-primary-hover-bg);
    --pico-primary-hover-border: var(--gh-btn-primary-border);
    --pico-primary-inverse: var(--gh-fg-on-emphasis);

    /* .secondary = GitHub default button; a.secondary = muted link. */
    --pico-secondary: var(--gh-fg-muted);
    --pico-secondary-hover: var(--gh-fg-accent);
    --pico-secondary-underline: transparent;
    --pico-secondary-hover-underline: var(--gh-fg-accent);
    --pico-secondary-focus: var(--gh-fg-accent);
    --pico-secondary-background: var(--gh-btn-bg);
    --pico-secondary-border: var(--gh-btn-border);
    --pico-secondary-hover-background: var(--gh-btn-hover-bg);
    --pico-secondary-hover-border: var(--gh-btn-border);
    --pico-secondary-inverse: var(--gh-fg-default);

    --pico-contrast: var(--gh-fg-default);
    --pico-contrast-hover: var(--gh-fg-accent);
    --pico-contrast-focus: var(--gh-fg-accent);
    --pico-contrast-background: var(--gh-btn-bg);
    --pico-contrast-border: var(--gh-btn-border);
    --pico-contrast-hover-background: var(--gh-btn-hover-bg);
    --pico-contrast-hover-border: var(--gh-btn-border);
    --pico-contrast-inverse: var(--gh-fg-default);

    --pico-box-shadow: var(--gh-shadow-overlay);
    --pico-button-box-shadow: var(--gh-shadow-resting);
    --pico-button-hover-box-shadow: var(--gh-shadow-resting);

    --pico-card-background-color: var(--gh-bg-default);
    --pico-card-border-color: var(--gh-border-default);
    --pico-card-box-shadow: 0 0 0 1px var(--gh-border-default);
    --pico-card-sectioning-background-color: var(--gh-bg-subtle);

    --pico-dropdown-background-color: var(--gh-bg-overlay);
    --pico-dropdown-border-color: var(--gh-border-default);
    --pico-dropdown-box-shadow: var(--gh-shadow-overlay);
    --pico-dropdown-color: var(--gh-fg-default);
    --pico-dropdown-hover-background-color: var(--gh-bg-neutral-muted);

    --pico-modal-overlay-background-color: var(--gh-backdrop);
    --pico-modal-overlay-backdrop-filter: none;

    --pico-form-element-background-color: var(--gh-bg-default);
    --pico-form-element-selected-background-color: var(--gh-bg-subtle);
    --pico-form-element-border-color: var(--gh-border-default);
    --pico-form-element-color: var(--gh-fg-default);
    --pico-form-element-placeholder-color: var(--gh-fg-muted);
    --pico-form-element-active-background-color: var(--gh-bg-default);
    --pico-form-element-active-border-color: var(--gh-fg-accent);
    --pico-form-element-focus-color: var(--gh-fg-accent);
    --pico-form-element-invalid-border-color: var(--gh-fg-danger);
    --pico-form-element-invalid-active-border-color: var(--gh-fg-danger);
    --pico-form-element-invalid-focus-color: var(--gh-fg-danger);
    --pico-form-element-valid-border-color: var(--gh-fg-success);
    --pico-form-element-valid-active-border-color: var(--gh-fg-success);
    --pico-form-element-valid-focus-color: var(--gh-fg-success);

    --pico-table-border-color: var(--gh-border-muted);
    --pico-table-row-stripped-background-color: transparent;

    --pico-code-background-color: var(--gh-bg-neutral-muted);
    --pico-code-color: var(--gh-fg-default);

    --pico-accordion-border-color: var(--gh-border-default);
    --pico-accordion-active-summary-color: var(--gh-fg-default);
    --pico-accordion-close-summary-color: var(--gh-fg-default);
    --pico-accordion-open-summary-color: var(--gh-fg-default);

    --pico-ins-color: var(--gh-fg-success);
    --pico-del-color: var(--gh-fg-danger);
}
```

### 4. Components Pico doesn't have

```css
/* Danger button */
button.danger, [role="button"].danger {
    --pico-background-color: var(--gh-btn-bg);
    --pico-border-color: var(--gh-btn-border);
    --pico-color: var(--gh-fg-danger);
}
button.danger:is(:hover, :focus-visible), [role="button"].danger:is(:hover, :focus-visible) {
    --pico-background-color: var(--gh-btn-danger-hover-bg);
    --pico-border-color: var(--gh-btn-danger-hover-bg);
    --pico-color: var(--gh-fg-on-emphasis);
}

/* GitHub has no outline buttons: Pico's .outline renders as a default button. */
button.outline, [role="button"].outline {
    --pico-background-color: var(--gh-btn-bg);
    --pico-border-color: var(--gh-btn-border);
    --pico-color: var(--gh-fg-default);
}

/* State labels (filled pill) */
.state {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 2em;
    font-weight: 500;
    line-height: 1.25;
    color: var(--gh-fg-on-emphasis);
    background-color: var(--gh-neutral-emphasis);
}
.state:is([data-state="open"], [data-state="in-progress/open"]) { background-color: var(--gh-success-emphasis); }
.state:is([data-state="merged"], [data-state="merged/completed"]) { background-color: var(--gh-done-emphasis); }
.state:is([data-state="closed"], [data-state="failed"]) { background-color: var(--gh-danger-emphasis); }
.state[data-state="pending-release"] { background-color: var(--gh-attention-emphasis); }

/* Review labels (outlined pill) */
.label {
    display: inline-block;
    padding: 0 0.5rem;
    border: 1px solid currentColor;
    border-radius: 2em;
    font-size: 0.857rem;
    font-weight: 500;
    color: var(--gh-fg-muted);
}
.label[data-state="accepted"] { color: var(--gh-fg-success); }
.label[data-state="rejected"] { color: var(--gh-fg-danger); }
.label[data-state="pending"]  { color: var(--gh-fg-attention); }
.label[data-state="needinfo"] { color: var(--gh-fg-accent); }

/* Counter */
.counter {
    display: inline-block;
    min-width: 1.5em;
    padding: 0 0.4rem;
    border-radius: 2em;
    font-size: 0.857rem;
    font-weight: 500;
    line-height: 1.5;
    text-align: center;
    vertical-align: middle;
    color: var(--gh-fg-default);
    background-color: var(--gh-bg-neutral-muted);
}

/* htmx loading state */
form.htmx-request [type="submit"],
button.htmx-request {
    opacity: 0.5;
    pointer-events: none;
    cursor: progress;
}
.htmx-indicator { opacity: 0; transition: opacity 150ms ease; }
.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator { opacity: 1; }
```

The other components (app header, data tables, flash, toast, blank slate, sidebar, pagination, footer)
follow the specs in [Components](#components), using only the `--gh-*` tokens.

### Shared partials

Repeated markup lives in `templates/partials/`:

| Partial | Context | Renders |
|---|---|---|
| `pagination.html` | `page_obj` | Pagination row (see Pagination) |
| `filter_fields.html` | `fields` (list of bound form fields) | Filter inputs in a `.grid`, checkboxes with inline labels |
| `review_table.html` | `reviews` | Reviews `data-table` with review labels, or a blank slate |
| `logo.svg` | — | Inline logo mark (see Logo) |
