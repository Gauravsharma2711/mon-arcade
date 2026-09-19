/**
 * MON ARCADE — Design Tokens
 * Source of truth: DESIGN_SYSTEM.md
 * 
 * Direction: Retro-modern arcade, professionally restrained.
 * Target: Classic arcade + modern product UX.
 */

export const ARCADE_COLORS = {
  // Backgrounds
  bg: '#07070b',
  bgRaised: '#0b0b12',

  // Surfaces
  panel: '#11111a',
  panelRaised: '#171722',
  panelBorder: '#292938',

  // Typography / Neutral
  text: '#f3f3f3',
  muted: '#9b9ba8',
  subtle: '#666675',

  // Accents (Restrained neon, one primary accent per screen)
  accent: '#8cff00', // Monad Lime (Default brand)
  lime: '#8cff00',
  cyan: '#35e8ff',   // Vault
  pink: '#ff3ea5',   // Bluff
  warning: '#ffd23f', // Countdown / alert
  danger: '#ff4d5a',  // Bust / breach / error
} as const;

export type AccentColor = 'lime' | 'cyan' | 'pink' | 'warning' | 'danger';

/**
 * Screen Accent Mapping per DESIGN_SYSTEM.md Section 2:
 * Home -> Lime
 * Bluff -> Pink
 * Bluff Result -> Lime
 * Vault -> Cyan
 * Vault Result -> Lime
 * Sponsor -> Neutral / Lime
 */
export const SCREEN_ACCENTS = {
  home: 'lime',
  bluff: 'pink',
  bluffResult: 'lime',
  vault: 'cyan',
  vaultResult: 'lime',
  sponsor: 'lime',
} as const;

export type ScreenVariant = keyof typeof SCREEN_ACCENTS;

/**
 * Spacing Scale per DESIGN_SYSTEM.md Section 5:
 * 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64
 */
export const ARCADE_SPACING = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  6: '24px',
  8: '32px',
  12: '48px',
  16: '64px',
} as const;

/**
 * Typography Roles per DESIGN_SYSTEM.md Section 3:
 * - Display / Pixel-inspired: game titles, major scores, timers, outcomes, hero headings
 * - Clean Sans-serif: body text, descriptions, forms, navigation, wallet/status, sponsor
 * - Mono: wallet addresses, transaction IDs, match IDs, technical states
 */
export const ARCADE_TYPOGRAPHY = {
  display: {
    fontFamily: '"Press Start 2P", monospace',
    roles: 'Game titles, major scores, timers, outcomes, hero headings',
  },
  sans: {
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
    roles: 'Body text, descriptions, forms, navigation, wallet/status UI, sponsor UI',
  },
  mono: {
    fontFamily: '"JetBrains Mono", monospace',
    roles: 'Wallet addresses, transaction IDs, match IDs, technical states',
  },
} as const;

/**
 * Surfaces & Borders per DESIGN_SYSTEM.md Section 4:
 * - Dark backgrounds
 * - 1px borders (standard)
 * - 2px borders (selected / active)
 * - Small radius
 * - Restrained shadows
 */
export const ARCADE_SURFACES = {
  panelBorderWidth: '1px',
  panelBorderWidthActive: '2px',
  borderRadius: {
    sm: '2px',
    DEFAULT: '4px',
    md: '6px',
    lg: '8px',
    full: '9999px',
  },
  shadows: {
    lime: '0 0 16px -2px rgba(140, 255, 0, 0.25)',
    pink: '0 0 16px -2px rgba(255, 62, 165, 0.25)',
    cyan: '0 0 16px -2px rgba(53, 232, 255, 0.25)',
    panel: '0 4px 24px -2px rgba(0, 0, 0, 0.6)',
  },
} as const;
