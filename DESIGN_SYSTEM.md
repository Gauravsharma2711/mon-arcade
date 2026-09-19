# MON ARCADE — Design System

## 1. Direction

**Retro-modern arcade, professionally restrained.**

Target: **classic arcade + modern product UX**.

Use:
- dark arcade environments
- pixel-inspired display typography
- clean sans-serif body text
- tactile controls
- restrained neon accents
- subtle CRT atmosphere
- strong hierarchy and spacing

Avoid:
- old emulator UI
- crypto-dashboard UI
- cyberpunk overload
- constant animation
- visual effects that reduce readability

**Rule: retro visuals, modern UX, professional restraint.**

---

## 2. Core Tokens

```css
--bg: #07070b;
--bg-raised: #0b0b12;

--panel: #11111a;
--panel-raised: #171722;
--panel-border: #292938;

--text: #f3f3f3;
--muted: #9b9ba8;
--subtle: #666675;

--accent: #8cff00;
--cyan: #35e8ff;
--pink: #ff3ea5;
--warning: #ffd23f;
--danger: #ff4d5a;
```

### Color rules

- Use **one primary accent per screen**.
- Keep most UI neutral and dark.
- Use accent colors for hierarchy and meaningful states.
- Do not use every accent simultaneously.
- Neon is a highlight, not a background.
- Glow is restrained.

### Screen accents

| Screen | Accent |
|---|---|
| Home | Lime |
| Bluff | Pink |
| Bluff Result | Lime |
| Vault | Cyan |
| Vault Result | Lime |
| Sponsor | Neutral / Lime |

---

## 3. Typography

Use three roles:

**Display / Pixel-inspired**
- game titles
- major scores
- timers
- outcomes
- hero headings

**Clean Sans-serif**
- body text
- descriptions
- forms
- navigation
- wallet/status UI
- sponsor UI

**Mono**
- wallet addresses
- transaction IDs
- match IDs
- technical states

Do not make every label pixel-styled. Functional UI must remain clean and readable.

---

## 4. Surfaces

Panels use:
- dark backgrounds
- 1px borders
- 2px borders for selected/high-priority states
- small radius
- restrained shadows
- consistent padding
- clear alignment

Avoid:
- glassmorphism
- huge blur
- giant gradients
- excessive glow
- decorative borders everywhere

Hierarchy:

```text
Background
  ↓
Panel
  ↓
Raised Panel
  ↓
Selected / Active
```

---

## 5. Layout

Spacing scale:

```text
4 / 8 / 12 / 16 / 24 / 32 / 48 / 64
```

Desktop:
- full arcade composition
- strong visual hierarchy
- game content is dominant

Mobile:
- stacked panels
- thumb-friendly controls
- readable text
- no horizontal overflow
- reduced decoration where necessary

---

## 6. Backgrounds

Major screens may have lightweight themed environments:

| Screen | Direction |
|---|---|
| Home | Dark arcade room |
| Bluff | Duel cabinet / neon arena |
| Bluff Result | Victory CRT stage |
| Vault Setup | Cyber vault room |
| Vault Battle | Giant vault chamber |
| Vault Result | Opened / locked vault |
| Sponsor | Arcade marquee |

Backgrounds are **decorative only**.

Preferred implementation:

```text
Optimized image
    >
CSS effects
    >
Canvas/WebGL
```

Use WebGL only when genuinely necessary.

Backgrounds must never control game logic.

---

## 7. CRT

CRT is optional atmosphere, never a usability requirement.

Use subtle:
- scanlines
- vignette
- noise
- localized glow

Keep effects behind content and preserve readability.

Respect:

```css
prefers-reduced-motion
```

---

## 8. Core Components

Build reusable components:

```text
ArcadeShell
ArcadeHeader
PageContainer
BackgroundScene
ArcadeButton
GameCard
Panel
Modal
Toast
Hud
Timer
StatBar
MatchLog
SponsorBadge
TransactionState
LoadingState
```

Do not turn pages into giant single components.

---

## 9. Buttons

Support:
- Primary
- Secondary
- Tertiary

States:
- default
- hover
- pressed
- focus
- disabled
- loading
- success
- error

Feedback should be fast and restrained.

---

## 10. Game UI Hierarchy

### Bluff

```text
Secret Number
    ↓
Opponent
    ↓
Countdown
    ↓
Push / Fold
    ↓
Round Status
```

### Vault

```text
Warden / Attacker
    ↓
Vault / Pot
    ↓
Turn
    ↓
Live Dialogue
    ↓
Release Event
```

---

## 11. Results

Result screens follow:

```text
Outcome
  ↓
Game Result
  ↓
Monad Confirmation
  ↓
Rematch / Arcade
```

---

## 12. Sponsor UI

Hierarchy:

```text
Game
  >
Game Action
  >
Game State
  >
Sponsor
```

Sponsor UI must:
- be visible but secondary
- never block controls
- never change game rules
- never fake system actions
- use Mon Arcade fallback branding when no sponsor exists

---

## 13. Async & Error States

Use meaningful states:

```text
IDLE
LOADING
CONNECTING
WAITING
CONFIRMING
ACTIVE
SUCCESS
FAILED
RETRY
```

Explain failures clearly and preserve user context.

---

## 14. Accessibility & Performance

Required:
- readable contrast
- visible focus states
- text labels for important states
- color is never the only state indicator
- keyboard support
- reduced-motion support
- responsive layout

Prefer:
- CSS/2D effects
- lazy-loaded game routes
- compressed artwork
- localized timers/state updates

Avoid:
- unnecessary rerenders
- heavy WebGL
- autoplay video
- animation loops in React render
- unnecessary dependencies

---

## 15. Hard Rules

1. No generic SaaS UI.
2. No crypto-dashboard styling.
3. No all-neon interface.
4. No excessive animation.
5. No heavy parallax/particles.
6. No WebGL for ordinary UI.
7. Never sacrifice readability for atmosphere.
8. Sponsor never overpowers the game.
9. UI never decides the authoritative winner.
10. **Make it feel expensive, but keep the implementation cheap.**
