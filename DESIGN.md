# OBS Flow — Design System (classless)

> GitHub (Primer) look, plain semantic HTML, mostly classless, one hand-written stylesheet (`static/css/flow.css`), no framework. Light **and** dark.

The reference is the GitHub *application* UI (PR list, PR page, settings), not the marketing site.
14px system type, 6px corners, hairline borders instead of shadows, blue links and focus, green only for the main action, coloured pills for state.
No glass, glows, gradients, display type, web fonts.

## Constraints

- **No Node.js, no build step, no dependencies.** CSS and JS are static files. htmx is vendored in `static/vendor/htmx/`.
- **No classes in templates.** CSS targets elements, ARIA attributes and structure (parent/child).
  Exceptions are hooks owned by other code (`htmx-*` classes, `debounce-countdown` / `countdown-timer` JS hooks),
  and a few structural helpers where HTML lacks a native element: `.icon` (for SVG sizing), `.tabs` and `.tab-content` (for CSS-only tab panels).
- **Two extension attributes, nothing else:**
  - `data-variant`: `primary | danger | success | warning`
  - `data-state`: object or review state (closed set below)
  - (`data-label` on table cells and `data-empty` on `article` are structural markers, see Components.)
- **No hacks:** no `!important`, no `@layer`, no specificity tricks, no hidden-checkbox state machines, no selectors on ids.
- **No inline `style`,** except the user's font size on `<html>`.
- **No hex values in templates.** The only colour literal outside `flow.css` is the logo accent in `partials/logo.svg`.
- **One layout breakpoint, 768px** (table cards). Everything else is fluid (flex/grid wrap).

## What we deliberately do not have

Do not add these back without a design decision:
outline buttons, shadows on buttons or cards, zebra striping, numbered pagination, custom checkbox/radio drawing (native + `accent-color`),
custom dropdown arrow art (a `▾` character), toast fade-in, backdrop blur, a separate "review label" style, second active-tab colour,
a "select mode" on mobile, per-theme duplicated CSS blocks.

## Themes

`color-scheme` follows the OS. `<html data-theme="light|dark">` forces one (no attribute = auto).
Every colour token is declared once with `light-dark(<light>, <dark>)`. Needs Firefox 120+, Chrome 123+, Safari 17.5+.

## Tokens

All in `:root`, prefix `--flow-`. Values are Primer "light default" / "dark default".

| Group | Tokens |
|---|---|
| Type | `font` (system sans), `mono` |
| Background | `bg` (canvas, inputs, cards), `bg-subtle` (header bar, table head, buttons, dropdown, toast, `pre`), `bg-hover` (neutral tint: hover, `code`, counter), `bg-accent` (selected row, info notice, selection), `bg-success`, `bg-attention`, `bg-danger` (notices) |
| Foreground | `fg`, `fg-muted`, `fg-accent` (links, focus), `fg-success`, `fg-attention`, `fg-danger` |
| Solid (filled pills, primary button) | `solid-success`, `solid-success-hover`, `solid-done`, `solid-danger`, `solid-attention`, `solid-accent`, `solid-neutral`, `on-solid` (white) |
| Lines | `border`, `border-muted` (row dividers), `backdrop`, `shadow` (overlays only) |
| Shape | `radius` (6px) |

`data-variant="success|warning|danger"` sets two helpers, `--flow-c` (text/accent colour) and `--flow-c-bg` (tint); elements pick what they need.
Don't invent new colour pairs: Primer values meet WCAG AA.

## Typography

Base size is the user's preference (12–20px, default 14px), set as `font-size` on `<html>`. Everything else is `rem`, so controls scale too.

| Element | Size | Weight |
|---|---|---|
| `h1` (one per page) | 2rem | 400 |
| `h2` | 1.5rem | 600 |
| `h3` | 1.25rem (1rem in dialogs) | 600 |
| `h4` | 1rem (0.857rem muted in `aside`) | 600 |
| body, `td` | 1rem | 400 |
| `small` | 0.857rem, muted | 400 |
| `code`, `pre` | 0.857rem mono | 400 |

`<h1>Fix build <small>#123</small></h1>`: `small` inside `h1` inherits the size, weight 300, muted.
`<small>` is the muted-text element everywhere (metadata, "unknown", "-", help text). Errors: `<small role="alert">` / `<p role="alert">` (red).
`p` directly after a page title row is muted (page description).

Spacing: 0.25 / 0.5 / 0.75 / 1 / 1.5 / 2.5rem. Block elements carry `margin-bottom: 1rem`, nothing else adds top margins.

## Element contract

| Markup | Looks like |
|---|---|
| `body > header` | App header bar (below) |
| `main` | Content column, max 1280px, 1rem side padding |
| `main > header` | Page title row: `h1` left, actions right |
| `main > section > h1 + p` | Home intro: large muted line |
| `main > details` | Filter panel box |
| `a` | Blue, underline on hover |
| `a[role=button]`, `button` | Default (grey) button |
| `[data-variant=primary]` on `button` / `a[role=button]` | Green button |
| `button[data-variant=danger]` | Red text, red fill on hover |
| `h4 > button` | Text action ("Edit") |
| `input, select, textarea` | 1px bordered field, accent border on focus |
| `input[type=checkbox\|radio]` | Native control, blue |
| `[aria-invalid=true]` | Red border |
| `fieldset[role=group]` | Joined input + button |
| `form > div`, `fieldset > div` | Auto-fit column grid for field rows |
| `form > footer`, `article > footer`, `td > footer`, `section > footer` | Right-aligned button row (left-aligned in `main > section`) |
| `table` | Bordered list (below) |
| `tbody th[scope=row]` | Object identifier: bold, text colour, blue on hover |
| `mark[data-state]` | State pill |
| `data` | Counter pill |
| `data[data-variant]` | Coloured inline text (yes / no) |
| `div[role=status]` | Inline notice, blue; with `data-variant` green / yellow / red |
| `article` | Bordered box with optional `header` / `footer` |
| `article[data-empty]` | Empty state |
| `dialog[open] > article` | Modal |
| `.tabs` | In-page tab panel (CSS-only) |
| `aside > section` | Sidebar block |
| `div:has(> aside)` | Detail layout: column + sidebar |
| `nav[aria-label=breadcrumb\|pagination]` | See below |
| `body > div[aria-live] > output` | Toasts |
| `body > footer` | Page footer |

## Components

### App header

`body > header`: `--flow-bg-subtle` bar, 1px bottom border. Two rows inside a 1280px column:

- **Top row** (`header > div`, min-height 3.5rem): brand `a` (inline `svg` 2rem + text, 1.143rem/600) left; `nav[aria-label=Account]` right.
- **Tabs** (`nav[aria-label=Main]`): links with 16px octicon + text, padding `0.375rem 0.5rem`, radius 6px, hover `--flow-bg-hover`.
  Current tab: `aria-current="page"`, weight 600, 2px accent underline. Wraps onto more rows when too narrow (nothing is ever cut off).
- **Account dropdown:** `details > summary + ul`, bordered summary, menu is right-aligned, radius 12px, overlay shadow. `▾` is added by CSS.
- Octicons are black SVGs: inverted in dark mode by a `header img` rule.

### Logo

Inline `partials/logo.svg`: base paths use `fill="currentColor"` (follows text colour in both themes), accent paths are `#32f773`.
Favicon: `static/img/logo.svg`. Don't recolour, add effects or place on a fill. Min 16px.

### Buttons

Height ≈ 32px, 1rem/500, radius 6px, sized to the label (never full width, except a lone button in an `aside` form).

| Variant | Markup |
|---|---|
| Default | `<button>` or `<a role="button">` |
| Primary | `data-variant="primary"` |
| Danger | `data-variant="danger"` |
| Text action | `<h4>Title <button>Edit</button></h4>` |

Rules:
- **A plain button is grey.** Primary is always explicit.
- At most **one primary** per form, dialog or toolbar: the action that moves forward (Save, Apply, Stage, Next, Log In).
- Destructive actions (Delete, Revoke) use `danger`, never primary.
- Cancel / Reset are default buttons, placed before the primary one.
- Disabled: 50% opacity, `not-allowed`.

### Forms

- `label`, `legend`: 1rem/600, block. A label wrapping a checkbox is 400.
- Fields: full width, `--flow-bg`, 1px `--flow-border`, radius 6px, same height as buttons. Focus: accent border plus 2px outline.
- Help text `<small>` directly after the field. Error: `aria-invalid="true"` on the field + `<small role="alert">`.
- Field caption: `<div><header><label>Title</label><label><input type=checkbox> Title exact</label></header><input></div>`; `div > header` puts the label left and its optional checkbox right-aligned with the input below (checkbox label 0.857rem).
- Field rows: put fields in `<div>`s inside a `div` that is a direct child of `form` / `fieldset`; they flow into columns of min 12rem.
- Joined input + button: `<fieldset role="group">`.
- Primary action row: `<footer>` as the last child of the `form` (not a `div`).

### Table

`<table>`: 1px border, radius 6px, `overflow: hidden`, 100% wide.

- `thead th`: `--flow-bg-subtle`, muted; sort links muted, accent on hover; direction shown as `▲` / `▼`.
- Rows: 1px `--flow-border-muted` dividers, padding `0.5rem 1rem`, hover `--flow-bg-subtle`, no striping.
- Selected row (`input[type=checkbox]:checked` inside): `--flow-bg-accent`.
- Identifier column: `<th scope="row">` in `tbody` holding the link.
- Checkbox column: any cell whose direct child is a checkbox is 2.5rem and centred. Header cells with no text use `aria-label`.
- **Under 768px:** rows are cards; each cell shows its `data-label` as a muted bold prefix. Every `td` / row `th` needs `data-label` (except checkbox and colspan cells).
- Cell actions: `<td><footer>…buttons…</footer></td>`.

### State pill and counter

`<mark data-state="{{ obj.state }}">{{ label }}</mark>`: 1rem/500, radius 2em, white on solid colour; 0.857rem and tighter inside `td`.

| `data-state` | Colour |
|---|---|
| `open`, `in-progress/open`, `accepted` | success (green) |
| `merged`, `merged/completed` | done (purple) |
| `closed`, `failed`, `rejected` | danger (red) |
| `pending-release`, `pending` | attention (yellow) |
| `needinfo` | accent (blue) |
| anything else (`draft`, `collecting`, `waiting`, `overridden`) | neutral (grey) |

The label text is always present; colour never carries meaning alone.
The values come from a closed set, so templates may print `data-state="{{ x.state }}"`. Attribute selectors handle `/`.

`<data value="12">12</data>`: counter after titles. 0.857rem/500, neutral pill.
`<data data-variant="success" value="yes">yes</data>`: plain coloured text (mergeable yes = success, no = danger). Unknown: `<small>unknown</small>`.

### Notices and toasts

- **Notice:** `<div role="status">` (blue) or with `data-variant="success|warning|danger"`. 1px border, 6px radius, 1rem padding, optional `h3` (1rem).
- **Toast:** server-rendered from Django messages: `<div aria-live="polite"><output data-variant="…">msg</output></div>` as a direct child of `body`, fixed bottom-right.
  Neutral card with a 4px left border in the variant colour (default accent). Hides itself via one CSS animation after 5s.
  `toasts.html` maps the Django tag `error` to `danger`.

### Box and empty state

`article`: 1px border, radius 6px, 1rem padding; `header` (bottom border) and `footer` (top border) are full-bleed.
Forms nested directly in articles (`article > form > footer`) have top spacing and a divider border before the action buttons.
Standalone button links (`article > a[role="button"]`, `.tab-content > a[role="button"]`) are right-aligned to match form footers.
Empty state: `<article data-empty><h3>No … found</h3><p>…</p></article>`: centred, muted, 2rem padding.

### Tabs (in-page)

CSS-only tabs using hidden radio inputs:
```html
<div class="tabs">
  <input type="radio" name="t" id="t1" checked><label for="t1">First</label>
  <input type="radio" name="t" id="t2"><label for="t2">Second</label>
  <hr>
  <div class="tab-content">…</div>
  <div class="tab-content">…</div>
</div>
```
Supports up to 3 tabs via the `~` sibling selector. Labels act as tab headers with a 2px accent underline when checked.

### Icons

SVGs use `class="icon"` to set standard sizing (1.15rem × 1.15rem) and `fill: currentColor`.

### Filter panel

`<details><summary>Search &amp; Filters</summary><form>…</form></details>` directly in `main`. Box with a subtle summary row, 1rem form padding.
Open when a filter is active. Actions in `form > footer`: Reset (default), Apply Filter (primary).

### Dialog

`<dialog open><form method="dialog" id="…-close"></form><article>…</article></dialog>`, inserted into `#modal-container` by htmx.
`dialog[open]` is a fixed full-screen overlay (`--flow-backdrop`, no blur), `article` centred, max 40rem, radius 12px, overlay shadow.
Header `h3` is 1rem. Buttons live in `article > footer`; a submit that belongs to an inner form is placed in that form's own `footer` or uses `form="id"`. Close: Escape and Cancel.

### Detail layout and sidebar

```html
<div>
  <div><section>…</section><section>…</section></div>
  <aside><section><h4>Label</h4><p>Value</p></section>…</aside>
</div>
```

The main column is `3 1 28rem`, the sidebar `1 1 14rem`; they wrap when narrow, so there is no media query.
`aside` is only used in this layout (the grid rule is `div:has(> aside)`).
Sidebar sections: bottom 1px border (not on the last), `h4` 0.857rem muted, values 1rem. Action forms: a single full-width button.

### Breadcrumb and pagination

Breadcrumb: `nav[aria-label=breadcrumb] > ul > li`; `/` is drawn by CSS, links muted, current item weight 600.
Pagination (`partials/pagination.html`): First / Previous, `<span aria-current="page">Page X of Y</span>`, Next / Last.
Disabled items are `<span aria-disabled="true">`. Links show a border on hover.

### Code

`code`: mono 0.857rem, `--flow-bg-hover`, padding `0.2em 0.4em`. `pre > code`: block on `--flow-bg-subtle`, border, scrolls horizontally.
SHAs: 8 chars, fingerprints: 12.

### Footer

`body > footer`: top border, 2.5rem padding, centred, 0.857rem muted. Links muted, accent on hover. Items separated by `·`.

## htmx

- Loading: htmx adds `htmx-request`. `form.htmx-request [type=submit]`, `button.htmx-request`: 50% opacity, no pointer events. `.htmx-indicator` fades in when it or an ancestor is `.htmx-request`.
- Errors come back as server-rendered dialogs or `div[role=status][data-variant=danger]`, never `alert()`.
- CSRF is sent through `hx-headers:inherited` on `<body>`.

## Motion and accessibility

- Only `opacity` and `transform`/`visibility`; hover changes are instant. `prefers-reduced-motion` disables all animation and transitions.
- Focus is always visible: 2px `--flow-fg-accent` outline on `:focus-visible`. Never remove it without a replacement.
- Active navigation uses `aria-current="page"`. Dialogs have a heading and close with Escape.
- State is never colour-only: pills and buttons carry text.

## Do / Don't

**Do**
- Reach for the element first (`mark`, `data`, `output`, `small`, `aside`, `footer`), then an ARIA attribute, then `data-variant` / `data-state`.
- Keep blue for links/focus/selection and green for the one primary button.
- Add new colours as a `--flow-*` token with `light-dark()`.
- Update this file in the same commit as any `flow.css` change.

**Don't**
- No `class` attributes (except htmx and JS hooks), no inline styles, no ids in selectors.
- No `!important`, `@layer`, `@media` other than the 768px table cards, reduced motion and the dark-mode icon inversion.
- No gradients, glows, blur, zebra rows, card shadows, web fonts, CDN assets.
- No green buttons for destructive actions; no blue buttons; no green links.

## Migration from Pico (done)

| Was | Is |
|---|---|
| `.container` | `main`, `body > header > *`, `body > footer` |
| `.app-header*`, `.app-brand`, `.app-tabs`, `.app-logo` | `body > header` structure, `aria-current` |
| `.page-header` | `main > header` |
| `.muted`, `.error`, `.text-success/danger` | `small`, `small[role=alert]`, `data[data-variant]` |
| `.counter` | `<data value>` |
| `.state`, `.state-sm`, `.label` | `<mark data-state>` |
| `.flash*` | `div[role=status][data-variant]` |
| `.toast*`, `#toast-container` | `output[data-variant]` in `div[aria-live]` |
| `.blankslate` | `article[data-empty]` |
| `.data-table`, `.striped`, `.id-link`, `.checkbox-cell` | plain `table`, `tbody th[scope=row]`, checkbox-in-cell |
| `.sidebar-section`, `.layout-with-sidebar` | `aside > section`, `div:has(> aside)` |
| `.filter-panel*` | `main > details > form` |
| `.grid`, `.actions` | `form > div`, `footer` |
| `.secondary`, `.outline` | plain button (default) |
| no class on `<button>` (was green) | `data-variant="primary"` |
| `.primary`, `.danger`, `.invisible` | `data-variant`, `h4 > button` |
| `a.secondary` | footer and breadcrumb links (by context) |
| `.dropdown*` | `header details` |
| select mode toggle, `.mobile-only`, `.table-toolbar` | removed |
| `.local-login-submit` + `:has(#id)` | submit moved into the login form's own `footer` |
| `--pico-*`, `--gh-*` | `--flow-*` |
