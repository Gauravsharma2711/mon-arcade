/**
 * Authoritative Bluff or Bust API Client.
 * 
 * Communicates with FastAPI backend. Strictly maintains state boundary:
 * React never decides outcomes; server owns state, hidden cards, and winners.
 */

export interface PlayerClientView {
  player_id: string;
  commitment_hash?: string | null;
  secret_value?: number | null;
  salt?: string | null;
  has_committed: boolean;
  action?: 'PUSH' | 'FOLD' | null;
}

export interface RevealedPlayerValue {
  player_id: string;
  secret_value: number;
  salt: string;
  commitment_hash: string;
  commitment_verified: boolean;
  action?: 'PUSH' | 'FOLD' | null;
}

export interface BluffMatchResult {
  match_id: string;
  status: string;
  winner_id?: string | null;
  loser_id?: string | null;
  is_tie: boolean;
  resolution_reason: string;
  creator_revealed: RevealedPlayerValue;
  opponent_revealed: RevealedPlayerValue;
  pot_amount: string | number;
  payout_tx_hash?: string | null;
  settlement_status: string;
  resolved_at: string;
}

export interface BluffMatchClientView {
  id: string;
  creator: PlayerClientView;
  opponent?: PlayerClientView | null;
  stake_amount: string | number;
  pot_amount: string | number;
  status: 'WAITING' | 'ACTIVE' | 'DECISION' | 'REVEALING' | 'RESOLVED' | 'CANCELLED';
  active_turn_player_id?: string | null;
  turn_seconds_allowed: number;
  seconds_remaining: number;
  can_act: boolean;
  is_creator: boolean;
  winner_id?: string | null;
  resolution_reason?: string | null;
  payout_tx_hash?: string | null;
  result?: BluffMatchResult | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface CreateMatchParams {
  creator_id: string;
  stake_amount: number;
  secret_value?: number;
  turn_seconds?: number;
}

export interface JoinMatchParams {
  player_id: string;
  secret_value?: number;
}

export interface CommitSecretParams {
  player_id: string;
  secret_value: number;
}

export interface SubmitDecisionParams {
  player_id: string;
  action: 'PUSH' | 'FOLD';
}

export type BluffActionAvailable = 'RETRY' | 'RETURN_TO_LOBBY' | 'VIEW_RESULT' | 'WAIT' | 'ACT';

/**
 * Structured API Error for Bluff or Bust.
 * Informs the UI whether the match is still alive and what action is available.
 */
export class BluffApiError extends Error {
  status: number;
  isMatchAlive: boolean;
  actionAvailable: BluffActionAvailable;
  rawDetail?: string;

  constructor(status: number, message: string, isMatchAlive?: boolean, actionAvailable?: BluffActionAvailable) {
    super(message);
    this.name = 'BluffApiError';
    this.status = status;

    if (isMatchAlive !== undefined && actionAvailable !== undefined) {
      this.isMatchAlive = isMatchAlive;
      this.actionAvailable = actionAvailable;
    } else if (status === 404) {
      this.isMatchAlive = false;
      this.actionAvailable = 'RETURN_TO_LOBBY';
    } else if (status === 410) {
      this.isMatchAlive = false;
      this.actionAvailable = 'VIEW_RESULT';
    } else if (status === 403) {
      this.isMatchAlive = true;
      this.actionAvailable = 'WAIT';
    } else if (status === 409 || status === 422 || status === 400) {
      this.isMatchAlive = true;
      this.actionAvailable = 'ACT';
    } else {
      // 0 (network down), 500, 502, 503
      this.isMatchAlive = true;
      this.actionAvailable = 'RETRY';
    }
  }
}

const API_BASE = '/api';

/**
 * Helper to parse backend error responses cleanly into structured BluffApiError.
 */
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) {
        errorDetail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // Ignore JSON parse error on non-JSON body
    }
    throw new BluffApiError(res.status, errorDetail);
  }
  return res.json();
}

/**
 * Robust fetch wrapper that translates network failures into clean BluffApiErrors.
 */
async function safeFetch<T>(url: string, init?: RequestInit): Promise<T> {
  try {
    const res = await fetch(url, init);
    return await handleResponse<T>(res);
  } catch (err: any) {
    if (err instanceof BluffApiError) {
      throw err;
    }
    // Network disconnection or ECONNREFUSED
    throw new BluffApiError(
      0,
      'Unable to connect to the game engine server. Your match state is preserved on the server.',
      true,
      'RETRY'
    );
  }
}

export const bluffApi = {
  /**
   * Fetch open lobbies waiting for an opponent.
   */
  async getOpenLobbies(): Promise<BluffMatchClientView[]> {
    return safeFetch<BluffMatchClientView[]>(`${API_BASE}/bluff/lobbies`);
  },

  /**
   * Fetch sanitized match state.
   */
  async getMatch(matchId: string, playerId?: string): Promise<BluffMatchClientView> {
    const query = playerId ? `?player_id=${encodeURIComponent(playerId)}` : '';
    return safeFetch<BluffMatchClientView>(`${API_BASE}/bluff/match/${encodeURIComponent(matchId)}${query}`);
  },

  /**
   * Restore match via universal endpoint.
   */
  async restoreMatch(matchId: string, playerId?: string): Promise<BluffMatchClientView> {
    const query = playerId ? `?player_id=${encodeURIComponent(playerId)}` : '';
    return safeFetch<BluffMatchClientView>(`${API_BASE}/match/${encodeURIComponent(matchId)}${query}`);
  },

  /**
   * Create a new duel with creator stake and hidden secret.
   */
  async createMatch(params: CreateMatchParams): Promise<BluffMatchClientView> {
    return safeFetch<BluffMatchClientView>(`${API_BASE}/bluff/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        creator_id: params.creator_id,
        stake_amount: params.stake_amount.toString(),
        secret_value: params.secret_value,
        turn_seconds: params.turn_seconds || 15,
      }),
    });
  },

  /**
   * Opponent joins an open duel.
   */
  async joinMatch(matchId: string, params: JoinMatchParams): Promise<BluffMatchClientView> {
    return safeFetch<BluffMatchClientView>(`${API_BASE}/bluff/match/${encodeURIComponent(matchId)}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },

  /**
   * Commit a secret value during ACTIVE phase.
   */
  async commitSecret(matchId: string, params: CommitSecretParams): Promise<BluffMatchClientView> {
    return safeFetch<BluffMatchClientView>(`${API_BASE}/bluff/match/${encodeURIComponent(matchId)}/commit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },

  /**
   * Submit PUSH or FOLD decision during DECISION phase.
   */
  async submitDecision(matchId: string, params: SubmitDecisionParams): Promise<BluffMatchClientView> {
    return safeFetch<BluffMatchClientView>(`${API_BASE}/bluff/match/${encodeURIComponent(matchId)}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },

  /**
   * Trigger reveal or fetch verified reveal result.
   */
  async revealMatch(matchId: string, playerId?: string): Promise<BluffMatchResult> {
    return safeFetch<BluffMatchResult>(`${API_BASE}/bluff/match/${encodeURIComponent(matchId)}/reveal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId }),
    });
  },

  /**
   * Fetch authoritative match result.
   */
  async getResult(matchId: string, playerId?: string): Promise<BluffMatchResult> {
    const query = playerId ? `?player_id=${encodeURIComponent(playerId)}` : '';
    return safeFetch<BluffMatchResult>(`${API_BASE}/bluff/match/${encodeURIComponent(matchId)}/result${query}`);
  },

  /**
   * Creator cancels open match.
   */
  async cancelMatch(matchId: string, playerId: string): Promise<BluffMatchClientView> {
    return safeFetch<BluffMatchClientView>(`${API_BASE}/bluff/match/${encodeURIComponent(matchId)}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId }),
    });
  },
};
