# MON ARCADE — Current Project State

> Internal living state document. Describes the current architecture, features, integrations, configuration, deployment status, and release checklist.

---

## 1. Product Overview

**Mon Arcade** is a high-performance, retro-modern arcade gaming platform built for the Monad ecosystem.

- **Value Proposition**: Fast games, strange strategies, and real Monad state interactions.
- **Visual Direction**: Retro-modern restrained arcade aesthetics, dark surfaces, pixel display typography, clean body text, and single primary accent per screen.
- **Authoritative Rule**: The backend owns all game rules, turn timers, and victory outcomes. The frontend never computes winners or settlement amounts independently.

---

## 2. System Architecture

```text
               +-------------------------------------------+
               |        React 18 + Vite Frontend          |
               | (Tailwind CSS, Lucide, Wagmi, Viem)      |
               +---------------------+---------------------+
                                     | HTTP REST / SSE Stream
                                     v
               +---------------------+---------------------+
               |            FastAPI Backend                |
               | (Async Python, Pydantic, Uvicorn)         |
               +----------+-----------+-----------+--------+
                          |           |           |
            +-------------+     +-----+-----+     +------------+
            |                   |           |                  |
            v                   v           v                  v
+-----------+--------+  +-------+---+  +----+-------+  +-------+--------+
|    Game Engines    |  | Database  |  |     AI     |  |   Blockchain   |
| - Bluff or Bust    |  | (Postgres |  |  Provider  |  |     Service    |
| - Monad Vault      |  | asyncpg & |  | (Mock /    |  | (Mock / Monad  |
| - Challenges Engine|  | In-Memory)|  |  LLM Seam) |  |  Testnet Seam) |
+--------------------+  +-----------+  +------------+  +----------------+
```

### Architectural Seams & Boundaries
1. **Game Engine Seam**: Deterministic, pure domain engines (`BluffEngine`, `VaultEngine`) manage turns, timeouts, and resolution.
2. **Blockchain Service Seam (`BlockchainService`)**:
   - `MockBlockchain`: Deterministic local simulation of deposits, wagers, and payouts.
   - `MonadBlockchain`: Production interface ready for Monad Testnet RPC (`https://testnet-rpc.monad.xyz`, Chain ID `10143`).
3. **AI Provider Seam (`AgentProvider`)**:
   - `MockAgentProvider`: Offline, deterministic evaluator with keyword injection triggers and normalized stat reasoning traces.
   - `LLMAgentProvider`: Prepared for external inference models via environment variables.
4. **Sponsor Resolver (`SponsorResolver`)**:
   - Manages subordinate marquee placements across Home, Bluff Lobby, and Vault Setup.
   - Non-blocking resolution with zero impact on core gameplay.

---

## 3. Current Implemented Features

### 1. Bluff or Bust
- **Mechanic**: Fast 1v1 hidden-information duel with commit-reveal cryptography.
- **Flow**: Host creates duel with stake (1-100 MON) and locks SHA-256 hashed secret (1-10) -> Opponent joins and commits -> Turn-based Push or Fold decision -> Authoritative reveal proof and settlement.
- **Features**: Real-time turn countdown, simulated bot opponent for single-player testing, full cryptographic salt verification on result screen, instant rematch flow.

### 2. Monad Vault
- **Mechanic**: Cyber intrusion chamber pitting an Attacker against autonomous AI Warden Sentinel-9 over a growing treasury pot.
- **Flow**: Choose role (Attacker or Warden) -> Calibrate 100-point stat vector (Persuasion, Deception, Patience, Aggression vs Skepticism, Rigidity, Empathy, Memory) -> 8-turn conversational intrusion -> Warden evaluates breach -> Verified payout if containment fails.
- **Features**: Real-time Server-Sent Events (SSE) dialogue streaming, visual 8-turn meter, quick exploit injection presets, live cognitive reasoning traces.

### 3. Community Challenges & Bounties
- **Mechanic**: Decentralized escrow system allowing players to fund MON bounties on custom AI containment conditions.
- **Conditions Supported**: `ATTACKER_WINS` (Vault Breach), `WIN_WITHIN_5_TURNS` (Speedrun Breach), `WARDEN_DEFENDS` (Iron Fortress).
- **Flow**: Create bounty -> Listed on community board -> Challenger accepts and launches linked Vault match -> Engine adjudicates condition upon match resolution -> Bounty transitions to `CLAIMABLE` -> Winner claims escrowed payout.

### 4. First Blood / Early Arcade Player
- **Mechanic**: Automatic founding-player recognition on initial duel or vault participation.
- **Guarantees**: Exactly-once record creation per wallet address, permanent timestamp preservation, sequential pilot numbering (`PILOT NO. #X`).
- **Presentation**: Rendered prominently via `FirstBloodBadge` on game result and showdown screens.

### 5. Subordinate Sponsor Portal
- **Mechanic**: Secondary placement engine for ecosystem sponsors to fund arcade exposure.
- **Features**: Slot reservation (`HOME_MARQUEE`, `BLUFF_LOBBY`, `VAULT_SETUP`), real-time banner preview, budget validation, mock escrow deposit, and click/impression telemetry tracking.

---

## 4. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Vite 5, TypeScript 5.5, Tailwind CSS 3.4, React Router 6, Lucide Icons |
| **Web3 / Wallet** | Wagmi 2, Viem 2, TanStack Query |
| **Backend** | Python 3.12, FastAPI, Uvicorn, Pydantic v2, Pydantic Settings |
| **Database** | PostgreSQL 16 (optional in development; dual-mode in-memory fallback enabled), asyncpg |
| **Streaming** | Server-Sent Events (SSE) via Starlette EventSourceResponse |
| **Testing** | pytest, pytest-anyio, httpx |

---

## 5. Repository Structure

```text
mon-arcade/
├── backend/
│   ├── app/
│   │   ├── ai/            # AI Agent provider seam (Mock & LLM)
│   │   ├── api/           # FastAPI router endpoints (health, bluff, vault, challenge, sponsor, etc.)
│   │   ├── blockchain/    # BlockchainService seam (Mock & Monad RPC)
│   │   ├── db/            # Database pool, migrations runner, and repositories
│   │   ├── game/          # Pure game domain engines (Bluff, Vault, Challenges)
│   │   ├── models/        # Pydantic domain models and schemas
│   │   ├── sponsor/       # Sponsor placement resolver and metrics
│   │   ├── config.py      # Environment configuration loader
│   │   └── main.py        # ASGI application factory and middleware
│   ├── tests/             # Comprehensive test suites (206 unit/integration tests)
│   ├── requirements.txt   # Python dependencies
│   └── .env.example       # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI components (ArcadeShell, Button, Panel, Modal, Hud, etc.)
│   │   ├── games/         # Bluff or Bust and Monad Vault pages
│   │   ├── hooks/         # Custom React state and SSE hooks
│   │   ├── lib/           # API clients and Wagmi configuration
│   │   ├── pages/         # Home, Challenges, Admin, NotFound
│   │   ├── sponsor/       # Sponsor portal, campaign creation, detail
│   │   └── styles/        # CRT scanline effects, design tokens, animations
│   ├── index.html         # HTML entry point
│   ├── package.json       # Node dependencies and scripts
│   ├── tailwind.config.js # Custom arcade color tokens and utilities
│   └── vite.config.ts     # Vite configuration and server proxy
├── migrations/            # Versioned PostgreSQL SQL schemas (001 through 006)
├── .gitignore             # Production git ignore configuration
├── .env.example           # Root environment variable template
├── DESIGN_SYSTEM.md       # Visual tokens and design guidelines
├── SKILL.md               # UI implementation rules
├── README.md              # Public documentation
└── brain.md               # Current project state (this file)
```

---

## 6. Integrations & Configuration

### Environment Variables

Configured via `.env` in root or respective subdirectories:

```env
# Backend
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mon_arcade
USE_MOCK_BLOCKCHAIN=true
USE_MOCK_AI=true

# Monad Testnet Configuration
MONAD_RPC_URL=https://testnet-rpc.monad.xyz
MONAD_CHAIN_ID=10143
PRIVATE_KEY=<deployer_private_key>

# Gemini AI Configuration
GEMINI_API_KEY=<gemini_api_key>
GEMINI_MODEL=gemini-2.5-flash

# Smart Contract
VAULT_CONTRACT_ADDRESS=0x5742Ec7A82D85248C76C266CCA9f61791aA133f6

# Frontend
VITE_API_URL=http://localhost:8000
VITE_MONAD_RPC_URL=https://testnet-rpc.monad.xyz
VITE_MONAD_CHAIN_ID=10143
```

### Seams Behavior
- When `USE_MOCK_BLOCKCHAIN=true`, the backend generates deterministic, verified transaction proofs locally without broadcasting to the Monad network.
- When `USE_MOCK_BLOCKCHAIN=false`, `MonadBlockchain` submits real transactions to Monad Testnet and settles matches via `MonArcadeVault`.
- When `USE_MOCK_AI=true`, the AI engine runs deterministic pattern evaluation without consuming external API credits.
- When `USE_MOCK_AI=false`, `GeminiAgentProvider` calls Google Generative AI (`gemini-2.5-flash`) for dynamic Sentinel-9 Warden dialogue with safe error fallbacks.

---

## 7. Deployment State

- **Frontend**: Compiles cleanly with Vite (`tsc -b && vite build`), producing optimized chunks with code-splitting and real Monad explorer link support.
- **Backend**: ASGI application verified with Uvicorn, FastAPI docs (`/docs`), and 100% passing test suite.
- **Smart Contracts (Monad Testnet - Chain ID 10143)**:
  - Contract: `MonArcadeVault`
  - Address: `0x5742Ec7A82D85248C76C266CCA9f61791aA133f6`
  - Deployment Tx: `0x7a7b6b44b586f39c3972774c0c3166f9b314a447a100690276818a536a190ed3`
  - Block: `63865677`
  - Deployer: `0xCDb486C9B4Aea600cBcD421D5e81550301F29a7b`
  - Onchain Bytecode: Verified (3,291 bytes confirmed via RPC)
  - Real Test Settlement Tx: `0x094be5f8d306f9bd474d36ff440a14a6380a1e45ed1aa228717b426cb6552099` (CONFIRMED)
  - Explorer Verification: Unverified (Monad Testnet Explorer does not offer an open Etherscan-compatible programmatic API without proprietary API keys)

---

## 8. Known Blockers & Limitations

1. **Explorer Programmatic Verification**: `testnet.monadexplorer.com` does not expose an open Etherscan-compatible programmatic verification endpoint for hardhat-verify. Source verification requires an official explorer API key or manual web submission.
2. **Local PostgreSQL**: If PostgreSQL is not running on `localhost:5432`, the backend defaults to in-memory repositories. Data resets on process restart in this mode.

---

## 9. Release Readiness Checklist

- [x] **Smart Contract Deployed**: `MonArcadeVault` deployed and verified on Monad Testnet.
- [x] **Real Onchain Settlement Verified**: Real deposit and match settlement confirmed on Monad Testnet.
- [x] **Gemini AI Integrated**: `GeminiAgentProvider` operational with `gemini-2.5-flash` and safe error fallback.
- [x] **No Secrets Committed**: Working tree scanned; private keys and credentials excluded via `.gitignore`.
- [x] **Frontend Build**: `tsc -b && vite build` passes with zero errors.
- [x] **Backend Test Suite**: 206/206 tests passing with 100% pass rate.
- [x] **Responsive UX Verified**: Tested across mobile (320px–375px), tablet, and desktop viewports.
- [x] **Accessible Navigation**: Keyboard focus rings, ARIA roles, and `prefers-reduced-motion` zeroing implemented.
- [x] **No Internal Timeline Language**: Build-process references removed from public-facing code and documentation.
