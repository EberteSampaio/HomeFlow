---
name: Shared Ledger
colors:
  surface: '#fcf8fa'
  surface-dim: '#dcd9db'
  surface-bright: '#fcf8fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f5'
  surface-container: '#f0edef'
  surface-container-high: '#eae7e9'
  surface-container-highest: '#e4e2e4'
  on-surface: '#1b1b1d'
  on-surface-variant: '#45464d'
  inverse-surface: '#303032'
  inverse-on-surface: '#f3f0f2'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#271901'
  on-tertiary-container: '#98805d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#fcdeb5'
  tertiary-fixed-dim: '#dec29a'
  on-tertiary-fixed: '#271901'
  on-tertiary-fixed-variant: '#574425'
  background: '#fcf8fa'
  on-background: '#1b1b1d'
  surface-variant: '#e4e2e4'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  container-max: 1200px
  gutter: 24px
  margin-mobile: 16px
---

## Brand & Style
The design system is built on a foundation of **Minimalism** and **Modern Professionalism**. It targets couples who require a shared, transparent view of their financial health without the cognitive load often associated with enterprise ERPs. 

The aesthetic is "Quiet Utility"—an environment that feels calm, organized, and high-end. It prioritizes clarity and trust through generous whitespace and a restricted color palette, ensuring that financial data remains the primary focus. Interaction patterns are intentional and subdued, avoiding aggressive transitions or loud decorative elements in favor of a refined, utilitarian experience.

## Colors
The palette is centered around **Deep Navy** (Primary) for authoritative elements like headers and primary actions, and **Slate Grays** (Secondary) for supporting information and UI iconography. 

- **Primary (#0F172A):** Used for primary buttons, active navigation states, and high-level headings.
- **Secondary (#64748B):** Used for labels, secondary text, and inactive icons.
- **Background (#F8FAFC):** A soft off-white that reduces eye strain compared to pure white.
- **Surface (#FFFFFF):** Used for cards, modals, and input fields to create a clear layer of separation from the background.
- **Borders (#E2E8F0):** A subtle, low-contrast gray used for structural division without creating visual noise.

## Typography
This design system utilizes **Inter** for all roles to maintain a systematic, neutral, and highly legible appearance. 

- **Numerical Data:** For financial figures in dashboards, use `fontWeight: 600` or `700` to ensure they are immediately scannable.
- **Hierarchy:** Use `label-sm` in uppercase with Slate Gray for category headers to provide clear structural signposting without dominating the view.
- **Readability:** Line heights are slightly loosened (e.g., 1.5x for body text) to accommodate dense financial tables and lists.

## Layout & Spacing
The layout follows a **Fixed Grid** approach for desktop to keep financial statements readable, and a **Fluid Grid** for mobile. 

- **Grid:** A 12-column system is used for desktop (max-width 1200px). On mobile, a single-column layout with 16px side margins is standard.
- **Spacing Rhythm:** An 8pt linear scale is used for all padding and margins to ensure mathematical harmony. 
- **Density:** Financial tables should utilize "Comfortable" vertical padding (12px to 16px per row) to prevent data from feeling claustrophobic, facilitating better shared review sessions.

## Elevation & Depth
Depth is conveyed through **Low-Contrast Outlines** paired with **Ambient Shadows**. This design system avoids heavy drop shadows to maintain its minimalist professional profile.

- **Level 0 (Base):** Background color (#F8FAFC).
- **Level 1 (Surface):** Cards and main containers use a 1px border (#E2E8F0) and no shadow.
- **Level 2 (Interactive):** Elements like "Hovered Cards" or "Dropdowns" gain a soft, diffused shadow: `box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05)`.
- **Level 3 (Overlay):** Modals and sticky headers use a more pronounced but still light shadow: `box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08)`.

## Shapes
The shape language is **Soft**, utilizing small border radii to appear approachable yet precise.

- **Standard Elements:** Buttons and input fields use a 4px (0.25rem) radius.
- **Large Containers:** Cards and modals use an 8px (0.5rem) radius.
- **Data Visualizations:** Bar charts and progress bars should use subtle rounding (2px) on the caps to align with the overall UI.

## Components
- **Buttons:** Primary buttons are Solid Deep Navy with white text. Secondary buttons are Ghost style (1px Slate Gray border) or light Slate Gray backgrounds.
- **Input Fields:** Use a white background, 1px border (#E2E8F0), and 12px horizontal padding. On focus, the border color shifts to Primary Navy with a 2px outer "halo" of 10% opacity Navy.
- **Cards:** The primary container for financial data. They should have a 1px border and no shadow by default. Use internal padding of 24px (lg).
- **Chips:** Used for transaction categories (e.g., "Groceries," "Rent"). These use a light Slate Gray background with a darker Slate Gray text; they are not pill-shaped but follow the standard 4px roundedness.
- **Data Tables:** Minimalist rows with a 1px bottom border only. No vertical lines. The header row uses `label-sm` typography with a subtle background tint.
- **Shared Indicators:** Small avatars or initials (couples' icons) should appear next to shared transactions or comments to denote who performed an action.