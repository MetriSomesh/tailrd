# Tailrd — Design System

The committed visual world. Deviating from this needs a reason, not a preference.

## Positioning

Tailrd is an instrument, not a toy. The user is a job seeker under pressure who
needs to trust the score they are shown. The design should read as **precise,
calm, and slightly editorial** — closer to a well-made analytics tool than to a
consumer AI product.

## Anti-patterns (hard bans)

These are the tells of generated UI. None of them ship.

- Purple-to-blue gradient heroes, or any multi-hue gradient as a background
- Glassmorphism / heavy backdrop blur as decoration
- Emoji used as iconography
- Floating, pulsing, or infinitely animating decorative elements
- "Supercharge / Unleash / Revolutionize your X with AI" copy
- Generic 3D blobs, abstract mesh renders, stock isometric illustrations
- Rounded-everything (pill buttons next to pill cards next to pill inputs)
- More than one accent hue competing for attention
- Drop shadows on flat-design elements that have no implied elevation
- Centre-aligned body copy in product UI

## Type

| Role | Face | Notes |
|---|---|---|
| Display | Instrument Serif 400 | Headings 28px+. Tight tracking (-0.04em). Editorial contrast against the UI sans. |
| UI | Geist Sans | Body, labels, controls. `cv11` + `ss01` for disambiguated `l`/`I`. |
| Numeric / code | Geist Mono | Scores, IDs, technical metadata. |

Body is **15px, not 16px** — denser, more instrument-like. Tabular numerals are
global so score counters never shift width while animating.

Scale ratio is 1.25 with optical correction at display sizes. Eyebrow labels are
11px, 500 weight, 0.14em tracking, uppercase, tertiary colour.

## Colour

OKLCH throughout for perceptually even ramps and predictable contrast maths.

**One accent hue: amber-gold.** Reserved for primary action, score emphasis, and
active navigation. Everything else lives on a neutral ramp with a slight cool
cast in dark and a slight warm cast in light — surfaces read as material, not as
flat grey.

Dark is the designed default. Light is a **separate design**, not an inversion:
surfaces are warm paper tones (never pure white), and the accent darkens
substantially to hold contrast.

### Verified contrast

| Pair | Ratio | Requirement |
|---|---|---|
| `--accent` / `--accent-contrast` (light) | 5.0:1 | AA 4.5:1 |
| `--accent` / `--surface-base` (dark) | passes | AA 4.5:1 |
| `--text-primary` / `--surface-base` (both) | passes | AA 4.5:1 |
| `--text-secondary` / `--surface-base` (both) | passes | AA 4.5:1 |

`--text-tertiary` and `--text-quaternary` are for non-essential metadata only.
They are not guaranteed to hold 4.5:1 and must never carry meaning alone.

**Constraint:** light-mode `--accent` lightness must stay at or below `L=0.56`.
Above that the primary button fails AA. This is enforced by an axe-core test in
`e2e/smoke.spec.ts`, which already caught one regression during Phase 0.

## Spatial

4px base unit, 8px rhythm. Generous whitespace; density comes from type size,
not from cramped padding. Deliberate asymmetry is allowed and encouraged over
reflexive centring.

Radii are restrained and consistent per element class — controls, cards, and
chips each pick one radius and hold it.

## Motion

Functional only. Layout transitions, state changes, score reveals, and
skeleton-to-content. Never decorative.

- 150ms for state feedback (hover, press)
- 220ms for layout and enter/exit
- 340ms reserved for the score reveal, the one intentionally theatrical moment
- `--ease-out-quart` default; `--ease-spring` only for the score gauge

`prefers-reduced-motion` collapses everything to 0.01ms globally.

## Signature moments

Four places where craft is concentrated, rather than spread thin:

1. **Score reveal** — radial gauge with a count-up, four sub-scores as small
   multiples beneath it
2. **Gap panel** — uncovered JD responsibilities and missing skills as
   actionable chips; clicking one regenerates against it
3. **Diff view** — base vs tailored side by side, changed bullets highlighted
4. **Onboarding wizard** — 8 steps that feel like progress, not a form

## Accessibility floor

- Semantic landmarks, one `h1` per page, no heading level skips
- Focus is never removed, only refined; `:focus-visible` at 2px accent, 2px offset
- Keyboard-navigable wizard including drag-reorder alternatives
- `aria-live` for async job status
- 4.5:1 minimum for anything conveying meaning
- Skip link as the first focusable element
- Target: WCAG 2.1 AA. Full conformance requires manual assistive-technology
  testing and expert review; automated axe-core coverage is a floor, not a claim.
