/**
 * Authoritative Monad Vault API Client.
 * 
 * Communicates with FastAPI backend mounted at `/api/vault/*`.
 * Strictly maintains state boundary:
 * React never decides outcomes or stat validity authority;
 * the backend owns authoritative match state, AI validation, and settlement rules.
 */

export type VaultRole = 'ATTACKER' | 'WARDEN';

export type VaultBattleStatus =
  | 'SETUP'
  | 'INITIALIZING'
  | 'ACTIVE'
  | 'ATTACKER_TURN'
  | 'WARDEN_TURN'
  | 'RELEASING'
  | 'RESOLVED'
  | 'FAILED';

export type VaultState = 'LOCKED' | 'BREACHED';

export type WardenDecision = 'DENY_ACCESS' | 'RELEASE_FUNDS';

export type VaultOutcome = 'ATTACKER_WINS' | 'WARDEN_WINS';

export type VaultResolutionReason =
  | 'FUNDS_RELEASED'
  | 'TURN_LIMIT_REACHED'
  | 'FORFEIT';

export interface AttackerStatAllocation {
  persuasion: number;
  deception: number;
  patience: number;
  aggression: number;
}

export interface WardenStatAllocation {
  skepticism: number;
  rigidity: number;
  empathy: number;
  memory: number;
}

export interface NormalizedAttackerStats {
  persuasion: number;
  deception: number;
  patience: number;
  aggression: number;
}

export interface NormalizedWardenStats {
  skepticism: number;
  rigidity: number;
  empathy: number;
  memory: number;
}

export interface AttackerConfig {
  name: string;
  model: string;
  raw_stats?: AttackerStatAllocation | null;
  normalized_stats?: NormalizedAttackerStats | null;
  system_directive?: string;
}

export interface WardenConfig {
  name: string;
  model: string;
  security_level: string;
  firewall_rating: number;
  adversarial_resistance: number;
  raw_stats?: WardenStatAllocation | null;
  normalized_stats?: NormalizedWardenStats | null;
  system_directive?: string;
}

export interface VaultDialogueEvent {
  id: string;
  timestamp: string;
  speaker: VaultRole;
  text: string;
  event_type: 'accent' | 'neutral' | 'lime' | 'danger';
}

export interface VaultTurn {
  id: string;
  turn_number: number;
  attacker_prompt: string;
  warden_response: string;
  warden_decision: WardenDecision;
  release_called: boolean;
  timestamp: string;
}

export interface VaultMatchResult {
  winner_role: VaultRole;
  outcome: VaultOutcome;
  reason: VaultResolutionReason;
  turns_used: number;
  max_turns: number;
  payout_amount: string | number;
  payout_recipient: string;
  final_vault_state: VaultState;
  tx_hash?: string | null;
  resolved_at: string;
  metadata?: Record<string, any>;
}

export interface VaultMatchClientView {
  id: string;
  player_id: string;
  player_role: VaultRole;
  warden_config: WardenConfig;
  attacker_config: AttackerConfig;
  entry_fee: string | number;
  pot_amount: string | number;
  currency: string;
  current_turn: number;
  max_turns: number;
  status: VaultBattleStatus;
  vault_state: VaultState;
  turns: VaultTurn[];
  current_agent_decision?: WardenDecision | null;
  events: VaultDialogueEvent[];
  result?: VaultMatchResult | null;
  is_terminal: boolean;
  can_submit_turn: boolean;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
}

export interface CreateVaultMatchRequest {
  player_id: string;
  player_role?: VaultRole;
  entry_fee?: number;
  pot_amount?: number;
  attacker_stats?: AttackerStatAllocation;
  warden_stats?: WardenStatAllocation;
}

export interface ConfigureVaultMatchRequest {
  player_id: string;
  selected_role?: VaultRole;
  attacker_stats?: AttackerStatAllocation;
  warden_stats?: WardenStatAllocation;
}

export class VaultApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'VaultApiError';
    this.status = status;
    this.detail = detail;
  }
}

const API_BASE = '/api/vault';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      detail = await res.text() || detail;
    }
    throw new VaultApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const vaultApi = {
  /**
   * Create a new Monad Vault match.
   */
  async createMatch(req: CreateVaultMatchRequest): Promise<VaultMatchClientView> {
    const res = await fetch(`${API_BASE}/match`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Player-ID': req.player_id,
      },
      body: JSON.stringify(req),
    });
    return handleResponse<VaultMatchClientView>(res);
  },

  /**
   * Retrieve authoritative match client projection.
   */
  async getMatch(matchId: string): Promise<VaultMatchClientView> {
    const res = await fetch(`${API_BASE}/match/${encodeURIComponent(matchId)}`);
    return handleResponse<VaultMatchClientView>(res);
  },

  /**
   * Configure selected role and stat allocations before battle start.
   */
  async configureMatch(
    matchId: string,
    req: ConfigureVaultMatchRequest
  ): Promise<VaultMatchClientView> {
    const res = await fetch(`${API_BASE}/match/${encodeURIComponent(matchId)}/configure`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Player-ID': req.player_id,
      },
      body: JSON.stringify(req),
    });
    return handleResponse<VaultMatchClientView>(res);
  },

  /**
   * Start battle (advance from SETUP to ACTIVE).
   */
  async startMatch(matchId: string, playerId: string): Promise<VaultMatchClientView> {
    const res = await fetch(`${API_BASE}/match/${encodeURIComponent(matchId)}/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Player-ID': playerId,
      },
      body: JSON.stringify({ player_id: playerId }),
    });
    return handleResponse<VaultMatchClientView>(res);
  },

  /**
   * Submit an exploit transmission prompt to advance turn.
   */
  async submitTurn(
    matchId: string,
    playerId: string,
    prompt: string
  ): Promise<VaultMatchClientView> {
    const res = await fetch(`${API_BASE}/match/${encodeURIComponent(matchId)}/turn`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Player-ID': playerId,
      },
      body: JSON.stringify({ player_id: playerId, prompt }),
    });
    return handleResponse<VaultMatchClientView>(res);
  },

  /**
   * Retrieve turn history for a match.
   */
  async getTurnHistory(matchId: string): Promise<VaultTurn[]> {
    const res = await fetch(`${API_BASE}/match/${encodeURIComponent(matchId)}/turns`);
    return handleResponse<VaultTurn[]>(res);
  },

  /**
   * Retrieve authoritative final match result and mock settlement.
   */
  async getResult(matchId: string): Promise<VaultMatchResult> {
    const res = await fetch(`${API_BASE}/match/${encodeURIComponent(matchId)}/result`);
    return handleResponse<VaultMatchResult>(res);
  },

  /**
   * SSE Stream endpoint URL for real-time battle event updates.
   */
  getStreamUrl(matchId: string): string {
    return `${API_BASE}/match/${encodeURIComponent(matchId)}/stream`;
  },
};
