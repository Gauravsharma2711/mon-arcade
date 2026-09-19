# Mon Arcade

> **Fast games. Strange strategies. Real Monad actions.**

Mon Arcade is a high-speed, retro-modern onchain gaming dApp built for the Monad ecosystem. It fuses deterministic server-authoritative gaming logic, autonomous AI agents, and frictionless Monad wallet interactions into a unified cyber-arcade experience.

---

## 🚀 Quick Links & Project Highlights

| Resource | Link | Details |
| :--- | :--- | :--- |
| 🌐 **Live Deployment** | [mon-arcade.onrender.com](https://mon-arcade.onrender.com/) | Live production web dApp deployed on Monad Testnet |
| 🎥 **Demo Walkthrough Video** | [Watch Demo Video (Google Drive)](https://drive.google.com/file/d/12is0JS__DG1TSuzHeshNSQpKnBMNZGMd/view?usp=sharing) | Full walkthrough of Bluff or Bust, Vault AI Warden, & Bounties |
| 📱 **Official Promotional Reel** | [Instagram Reel](https://www.instagram.com/reel/DddvZVHTl8W/?stkn=MXcyeDlvZjQ2OXUyeQ==) | High-energy product showcase and teaser video |
| 💼 **LinkedIn Announcement** | [LinkedIn Post](https://lnkd.in/p/dSH-pHkT) | Hackathon launch update & community release |
| 📈 **Social Traction** | **1,700+ Impressions** | Organic impressions and community engagement on socials |

---

## Value Proposition

Traditional onchain games suffer from sluggish tick rates, disjointed user experiences, and high transaction latency. Mon Arcade harnesses Monad's high-throughput, low-latency execution environment to deliver:
- **Instantaneous Gameplay**: Low-latency turn execution powered by server-sent events (SSE) and deterministic state machines.
- **Agentic Opponents**: True adversarial game states against autonomous AI agents that reason, counter, and react dynamically.
- **Verifiable Onchain Stakes**: Cryptographically verifiable commitments, escrowed bounties, and transparent reward distributions.
- **Sustainable Arcade Economics**: Built-in, non-intrusive sponsor placement engine that dynamically surfaces ecosystem projects to fund arcade prize pools.

---

## Features

- **Bluff or Bust**: High-stakes 1v1 hidden-information psychological duel with secret action commitments, wager multipliers, and bluff calls.
- **Monad Vault**: Single-player adversarial heist where players attempt to breach an autonomous AI Warden guarding an escalating onchain prize vault.
- **Arcade Challenges & MON Bounties**: Peer-to-peer bounty system where players stake MON to challenge others to beat target Vault metrics (e.g. breaching the Vault in under 3 turns).
- **First Blood / Early Arcade Player**: Automatic milestone recognition that records and honors early arcade participants with badges on result screens.
- **Sponsor System**: Self-service sponsor placement portal where brands can create campaigns, fund placement budgets, and dynamically stream brand messaging across arcade marquees.
- **Shared Arcade Shell**: Cohesive retro-modern arcade interface featuring subtle CRT phosphor bloom, tactile audio feedback, responsive mobile layouts, and strict keyboard accessibility.

---

## Game Overviews

### 1. Bluff or Bust
A rapid-fire 1v1 psychological duel of hidden commitments and bluff calling:
1. **Commit Phase**: Both players secretly commit their move (`POWER_MOVE`, `STEALTH_PROBE`, `OVERCLOCK`, `DATA_SIPHON`) and choose whether to declare a bluff.
2. **Reveal & Resolve**: The backend game engine deterministically calculates priority, counters, and multipliers.
3. **Showdown**: If a player accurately calls their opponent's bluff, they deal critical damage and capture momentum; an uncalled bluff rewards the bluffer with bonus tokens.
4. **Resolution**: Match concludes when a player's integrity drops to 0, settling onchain stakes and recording stats.

### 2. Monad Vault
An adversarial rogue-lite infiltration against an AI Warden:
1. **Infiltration**: Players enter a 5-turn breach sequence against the autonomous AI Warden.
2. **Action Selection**: Choose between *Terminal Exploit*, *Firmware Overload*, *Bypass Matrix*, or *Defensive Scramble*.
3. **AI Defense**: The AI Warden evaluates player actions and formulates dynamic defense protocols (`FIREWALL_SPIKE`, `NEURAL_COUNTER`, `SYSTEM_PURGE`).
4. **Breach or Lockout**: Infiltrate all defensive nodes before turn exhaustion to claim the prize vault, or trigger defensive lockout.

### 3. Community Bounties & Challenges
- Players can create custom Vault challenges with specified conditions (e.g., win Vault in $\le 3$ turns).
- Creators stake a bounty amount (in MON).
- Challenger accepts, completes the authorized Vault match, and if the target condition is achieved, the bounty status shifts to `CLAIMABLE`.

### 4. Sponsor System
- **Placement Locations**: Dynamic banner and marquee placements across the arcade header, game lobbies, and match victory screens.
- **CPM / Impression Budgeting**: Tracks impressions and decrements campaign balances.
- **Default Fallbacks**: When active sponsor campaigns are depleted or inactive, the system seamlessly displays native Mon Arcade ecosystem announcements.

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (React / Vite)                     │
│  - Shared Arcade Shell & HUD                                │
│  - Wagmi / Viem Web3 Connectors                            │
│  - EventSource SSE Game Stream                              │
└──────────────┬───────────────────────────────▲──────────────┘
               │ HTTP / SSE                    │ Updates
┌──────────────▼───────────────────────────────┴──────────────┐
│             Backend Engine (FastAPI / Python)                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Authoritative Game State Engine (Bluff & Vault FSM)    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Agent Seam (MockAI / Google Gemini 2.5 Flash)          │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Blockchain Seam (MockBlockchain / Monad EVM RPC)       │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Sponsor Placement Resolver & Campaign Engine           │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────┬───────────────────────────────▲──────────────┘
               │ SQL Queries                   │ Data
┌──────────────▼───────────────────────────────┴──────────────┐
│             Database (PostgreSQL / asyncpg)                 │
│  - Players & First Blood Records                            │
│  - Games, Turns, Action History                             │
│  - Sponsors, Campaigns, Placements                          │
│  - Challenges & Bounties                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

- **Frontend**:
  - React 18
  - TypeScript
  - Vite
  - TailwindCSS (custom retro-modern design system tokens)
  - Lucide React (tactile icons)
  - Wagmi & Viem (EVM wallet integration)
- **Backend**:
  - Python 3.11+
  - FastAPI (REST & Server-Sent Events)
  - Pydantic v2 (schema validation)
  - asyncpg (PostgreSQL asynchronous driver)
  - Web3.py & eth-account (Monad blockchain interface)
  - HTTPX (asynchronous LLM agent adapter)
- **Database**:
  - PostgreSQL 14+ (relational game, sponsor, and player state)

---

## Repository Structure

```text
mon-arcade/
├── backend/
│   ├── app/
│   │   ├── ai/            # AgentProvider interface & adapters (Mock, LLM)
│   │   ├── api/           # API endpoints (health, bluff, vault, challenge, sponsor, etc.)
│   │   ├── blockchain/    # BlockchainService interface & adapters (Mock, Monad RPC)
│   │   ├── config.py      # Pydantic BaseSettings environment config
│   │   ├── db/            # PostgreSQL connection pool & lifecycle
│   │   ├── game/          # Authoritative game logic, state machines, turn evaluators
│   │   ├── main.py        # FastAPI app initialization, CORS, lifespan
│   │   ├── models/        # Pydantic request/response and domain models
│   │   └── sponsor/       # Sponsor placement repository & resolver
│   ├── tests/             # Backend pytest integration and unit test suite
│   ├── requirements.txt   # Python production dependencies
│   ├── requirements-dev.txt# Python testing & development tools
│   └── .env.example       # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI (ArcadeShell, Header, HUD, FirstBloodBadge, Button)
│   │   ├── games/
│   │   │   ├── bluff/     # Bluff or Bust lobby, duel arena, result screen
│   │   │   └── vault/     # Monad Vault lobby, terminal battle, result screen
│   │   ├── hooks/         # Custom React hooks (wallet, sound, animations)
│   │   ├── lib/           # API client, Web3 configuration
│   │   ├── pages/         # Home, Challenges, Admin, Error pages
│   │   ├── sponsor/       # Sponsor dashboard, campaign creator, detail view
│   │   ├── styles/        # Global styles & arcade design system tokens
│   │   ├── App.tsx        # Application routing & layout shell
│   │   └── main.tsx       # Root entrypoint & providers
│   ├── package.json       # Node dependencies & scripts
│   ├── tsconfig.json      # TypeScript compiler configuration
│   ├── vite.config.ts     # Vite bundler configuration
│   └── .env.example       # Frontend environment template
├── migrations/
│   └── 001_initial_schema.sql # PostgreSQL DDL schema & indexes
├── .env.example           # Root environment configuration template
├── .gitignore             # Comprehensive git exclusion rules
├── brain.md               # Current technical status & architectural specification
├── DESIGN_SYSTEM.md       # Visual design specification & UI standards
├── LICENSE                # MIT License
└── README.md              # Public documentation
```

---

## Local Development Setup

Follow these steps to run Mon Arcade locally for development and testing.

### Prerequisites
- **Node.js**: `v18.0.0` or higher (`v20+` recommended)
- **Python**: `3.11` or higher
- **PostgreSQL**: `14` or higher (optional if running mock mode)
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/mon-arcade.git
cd mon-arcade
```

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
# On Linux/macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
```

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/health`

### 3. Frontend Setup
In a separate terminal:
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Launch Vite development server
npm run dev
```
The frontend application will be live at `http://localhost:3000`.

---

## Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PORT` | `int` | `8000` | Port for the FastAPI server |
| `HOST` | `string` | `0.0.0.0` | Host bind address |
| `ENVIRONMENT` | `string` | `development` | App environment (`development` / `production`) |
| `DATABASE_URL` | `string` | `postgresql://postgres:postgres@localhost:5432/mon_arcade` | PostgreSQL connection string |
| `USE_MOCK_BLOCKCHAIN` | `bool` | `true` | When `true`, uses in-memory simulated blockchain adapter |
| `USE_MOCK_AI` | `bool` | `true` | When `true`, uses deterministic heuristic AI agent |
| `MONAD_RPC_URL` | `string` | `https://rpc.monad.xyz` | Monad EVM RPC provider endpoint |
| `CHAIN_ID` | `int` | `10143` | Monad chain ID |
| `PRIVATE_KEY` | `string` | `""` | Arcade operator key (for onchain payout dispatching) |
| `ANTHROPIC_API_KEY` | `string` | `""` | Optional Anthropic API key for production LLM Warden |

### Frontend Configuration (`frontend/.env`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | `string` | `http://localhost:8000` | Backend API URL |
| `VITE_MONAD_RPC_URL` | `string` | `https://rpc.monad.xyz` | Monad RPC URL for wallet providers |
| `VITE_MONAD_CHAIN_ID` | `int` | `10143` | Chain ID for Monad Testnet |

---

## Database Setup

To run with full PostgreSQL persistence:

1. Create a local PostgreSQL database:
```sql
CREATE DATABASE mon_arcade;
```
2. Apply the schema migration:
```bash
# Using psql:
psql -U postgres -d mon_arcade -f migrations/001_initial_schema.sql
```
3. Update `DATABASE_URL` in `backend/.env` with your database credentials.

*Note: In development without a database configured, the backend can run in mock/simulation mode.*

---

## AI Configuration (Google Gemini)

Mon Arcade features a pluggable `AgentProvider` abstraction for Sentinel-9 Warden autonomous intelligence:
- **Mock AI (Default)**: Enabled via `USE_MOCK_AI=true`. Provides deterministic, fast responses for local testing without external API calls.
- **Gemini Agent**: Set `USE_MOCK_AI=false` and provide `GEMINI_API_KEY` (or `AI_API_KEY`) to enable dynamic conversational Warden responses and psychological defense strategies powered by Google Gemini (`gemini-2.5-flash`).
  - Model configurable via `GEMINI_MODEL=gemini-2.5-flash`
  - Strict server-side execution: API keys are never exposed to the client.
  - Safe error fallbacks: Automatically falls back to calibrated defense heuristics if the API times out or rate-limits.
  - Winner authority boundary: Gemini generates reasoning and dialogue, while the backend game engine authoritatively evaluates turn limits and breach conditions.

---

## Monad Testnet Configuration

Mon Arcade is configured to target the Monad Testnet:
- **Network Name**: Monad Testnet
- **Chain ID**: `10143`
- **RPC URL**: `https://testnet-rpc.monad.xyz`
- **Currency Symbol**: `MON`
- **Block Explorer**: `https://testnet.monadexplorer.com`

To switch from mock simulation to live Monad Testnet interactions:
1. In `backend/.env`, set `USE_MOCK_BLOCKCHAIN=false`.
2. Provide a funded `PRIVATE_KEY` for the operator wallet to settle contracts.
3. Configure `MONAD_RPC_URL=https://testnet-rpc.monad.xyz`.

---

## Smart Contract Deployment

The core escrow and settlement contract, `MonArcadeVault`, is deployed on Monad Testnet.

### Deployed Contract Details

| Field | Value |
| :--- | :--- |
| **Contract Name** | `MonArcadeVault` |
| **Network** | Monad Testnet (Chain ID `10143`) |
| **Contract Address** | [`0x5742Ec7A82D85248C76C266CCA9f61791aA133f6`](https://testnet.monadexplorer.com/address/0x5742Ec7A82D85248C76C266CCA9f61791aA133f6) |
| **Deployment Tx Hash** | [`0x7a7b6b44b586f39c3972774c0c3166f9b314a447a100690276818a536a190ed3`](https://testnet.monadexplorer.com/tx/0x7a7b6b44b586f39c3972774c0c3166f9b314a447a100690276818a536a190ed3) |
| **Deployment Block** | `63865677` |
| **Onchain Bytecode** | Confirmed (3,291 bytes) |
| **Verified Test Settlement** | [`0x094be5f8d306f9bd474d36ff440a14a6380a1e45ed1aa228717b426cb6552099`](https://testnet.monadexplorer.com/tx/0x094be5f8d306f9bd474d36ff440a14a6380a1e45ed1aa228717b426cb6552099) |
| **Verification Status** | Unverified *(Monad Testnet Explorer does not offer an open programmatic Etherscan-compatible API without private API keys)* |

### Contract Compilation & Testing
To compile and test smart contracts independently:
```bash
cd contracts
npm install
npm test
```
All 15 unit tests validate match deposits, duplicate prevention, authorized settlements, reentrancy guards, and emergency recovery.

---

## Public Demo

- **Live Web App**: `https://demo.mon-arcade.xyz` *(Placeholder - Deployment pending hosting setup)*
- **API Health Endpoint**: `https://api.mon-arcade.xyz/api/health` *(Placeholder)*

---

## Running Verification & Tests

### Backend Test Suite
```bash
cd backend
python -m pytest tests -v
```

### Frontend Build & Typecheck
```bash
cd frontend
npm run build
```

---

## Deploying to Render

Mon Arcade is configured for single-service cloud deployment on Render (Web Service + Render PostgreSQL), where FastAPI serves the API and the compiled React SPA.

### Option A: Render Blueprint (`render.yaml`)
1. Fork or push the repository to GitHub: `https://github.com/Gauravsharma2711/mon-arcade.git`.
2. In the [Render Dashboard](https://dashboard.render.com/), select **New > Blueprint**.
3. Connect your repository. Render will automatically detect [`render.yaml`](file:///c:/mon-arcade/render.yaml) and provision:
   - **`mon-arcade-db`**: PostgreSQL database.
   - **`mon-arcade`**: Web Service running the built fullstack application.
4. Set your secret environment variables in the Render Dashboard:
   - `PRIVATE_KEY`: Your funded Monad Testnet operator private key.
   - `GEMINI_API_KEY`: Your Google Gemini API key.

### Option B: Manual Render Setup
1. **Provision PostgreSQL**:
   - Create a new PostgreSQL instance named `mon-arcade-db`.
   - Copy the internal connection string (`DATABASE_URL`).
2. **Create Web Service**:
   - Create a new **Web Service** connected to your GitHub repository.
   - **Runtime**: `Python`
   - **Build Command**:
     ```bash
     npm --prefix frontend install && npm --prefix frontend run build && pip install -r backend/requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
     ```
3. **Configure Environment Variables**:
   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `ENVIRONMENT` | `production` | Enables production mode and real onchain settlements |
   | `DATABASE_URL` | *(internal DB connection string)* | Render PostgreSQL connection |
   | `USE_MOCK_BLOCKCHAIN` | `false` | Routes match settlements to Monad Testnet |
   | `USE_MOCK_AI` | `false` | Routes Sentinel-9 Warden intelligence to Gemini |
   | `MONAD_RPC_URL` | `https://testnet-rpc.monad.xyz` | Monad Testnet RPC endpoint |
   | `MONAD_CHAIN_ID` | `10143` | Chain ID for Monad Testnet |
   | `VAULT_CONTRACT_ADDRESS` | `0x5742Ec7A82D85248C76C266CCA9f61791aA133f6` | Deployed MonArcadeVault contract |
   | `GEMINI_MODEL` | `gemini-2.5-flash` | Configured Gemini AI model |
   | `PRIVATE_KEY` | *(secret)* | Operator wallet private key |
   | `GEMINI_API_KEY` | *(secret)* | Server-side Gemini API key |

On startup, FastAPI automatically connects to PostgreSQL, applies all schema migrations from `migrations/`, mounts the `/api` endpoints, and serves the optimized frontend at your live `.onrender.com` URL.

---

## Troubleshooting

- **CORS Errors**: Ensure `VITE_API_URL` in `frontend/.env` matches the port where your FastAPI server is running (`http://localhost:8000`).
- **Database Connection Refused**: Verify that PostgreSQL is running on the expected port and that the user credentials in `DATABASE_URL` are valid.
- **Port Conflicts**: If port `8000` or `3000` is in use, modify `PORT` in `backend/.env` or specify `--port <PORT>` for Vite in `frontend/package.json`.
- **Wallet Connection Issues**: Check that your browser wallet (e.g. MetaMask, Rabby) allows connection to the specified Monad network chain ID.

---

## Security & Disclosure

- **Private Keys**: Never commit private keys, mnemonic seed phrases, or sensitive API keys to the repository. The `.gitignore` is configured to exclude all `.env` files and key stores.
- **Authoritative Architecture**: Client-side state is treated as untrusted; all game outcomes, turn limits, damage calculations, and bounty validations are computed strictly on the backend game engine.
- **Reporting Vulnerabilities**: If you discover any security issue, please contact the maintainers directly or open a confidential security advisory.

---

## License

This project is licensed under the MIT License - see the [LICENSE](file:///c:/mon-arcade/LICENSE) file for details.
