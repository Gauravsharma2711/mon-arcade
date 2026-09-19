---
name: mon-arcade-ui
description: "Build Mon Arcade as a lightweight retro-modern arcade UI for screens, components, HUDs, sponsor placements, motion, responsive behavior, and visual effects."
---

# Mon Arcade UI Skill

## Goal

Build **classic arcade + modern product UX**.

Target: **premium arcade product, not neon spectacle**.

Avoid old-emulator UI, crypto-dashboard UI, cyberpunk overload, constant animation, and effects that hurt readability.

## Before Coding

1. Read `DESIGN_SYSTEM.md`.
2. Inspect the existing project.
3. Reuse existing tokens and components.
4. Identify whether work belongs to Shell, Bluff, Vault, or Sponsor.
5. Keep UI separate from game/business logic.

## Shared Components

Prefer:

```text
ArcadeShell
ArcadeHeader
PageContainer
BackgroundScene
GameCard
ArcadeButton
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

Do not build giant page components.

## Screen Priorities

**Home:** identity → two games → play actions → sponsor.

**Bluff Lobby:** create duel → join duel → QR/share.

**Bluff Match:** hidden number → opponent → timer → Push/Fold → round status.

**Bluff Result:** reveal → winner → Monad confirmation → rematch.

**Vault Setup:** role → stats → pot → Fight.

**Vault Battle:** Warden vs Attacker → turn → dialogue → vault → release.

**Vault Result:** winner → outcome → payout → challenge again.

**Sponsor:** short flow, placement preview before payment.

Sponsor stays secondary to gameplay.

## Motion

Motion communicates state, not decoration.

Good: button feedback, reveal, timer pulse, message entry, vault unlock, transaction confirmation.

Avoid: constant floating UI, heavy parallax, particle systems, long transitions, animation on everything.

Use CSS first. Use Framer Motion only when it adds real value.

## CRT & Backgrounds

CRT is optional atmosphere. Keep it subtle, behind UI, readable, and reduced-motion aware.

Preferred background approach:

```text
Optimized image > CSS effects > Canvas/WebGL
```

Use WebGL only when genuinely valuable. Backgrounds never control game logic.

## Sponsor Rules

Sponsor UI must:
- never block controls
- never change game rules
- never fake system actions
- use Mon Arcade fallback branding when no sponsor exists

Hierarchy:

```text
Game > Action > Game State > Sponsor
```

## Async States

Never show unexplained blank states. Use meaningful states such as:

```text
CONNECTING...
WAITING FOR OPPONENT...
CONFIRMING...
WARDEN THINKING...
ATTACKER THINKING...
REVEALING...
PAYMENT CONFIRMED
```

## Architecture

UI is presentation.

Authoritative game state and winner resolution belong to the backend/game engine.

Keep game logic, AI, blockchain, and sponsor resolution separate from visual components.

Do not invent unnecessary infrastructure.

## Quality

Check:
- desktop/mobile responsiveness
- keyboard focus
- reduced motion
- readable contrast
- loading/error states
- console errors
- unnecessary dependencies

**Final rule: make it feel expensive, but keep the implementation cheap.**
