/**
 * Mon Arcade — Challenge & Bounty API Client.
 * Communicates with backend endpoints at `/api/challenge/*`.
 */

export type ChallengeStatus = 'OPEN' | 'ACTIVE' | 'CONDITION_MET' | 'CLAIMED' | 'FAILED';

export type ChallengeCondition = 'ATTACKER_WINS' | 'WIN_WITHIN_5_TURNS' | 'WARDEN_DEFENDS';

export interface Challenge {
  id: string;
  creator_wallet: string;
  game: string;
  condition: string;
  condition_description: string;
  bounty_amount: number;
  status: ChallengeStatus;
  accepted_by?: string | null;
  winner_wallet?: string | null;
  match_id?: string | null;
  created_at: string;
  claimed_at?: string | null;
  claim_tx_hash?: string | null;
}

export interface CreateChallengeInput {
  creator_wallet: string;
  bounty_amount: number;
  condition: string;
  game?: string;
}

export class ChallengeApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ChallengeApiError';
    this.status = status;
    this.detail = detail;
  }
}

const API_BASE = '/api/challenge';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      detail = (await res.text()) || detail;
    }
    throw new ChallengeApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchChallenges(status?: ChallengeStatus): Promise<Challenge[]> {
  const url = status ? `${API_BASE}?status=${status}` : API_BASE;
  const res = await fetch(url);
  return handleResponse<Challenge[]>(res);
}

export async function fetchChallenge(id: string): Promise<Challenge> {
  const res = await fetch(`${API_BASE}/${id}`);
  return handleResponse<Challenge>(res);
}

export async function createChallenge(input: CreateChallengeInput): Promise<Challenge> {
  const res = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      creator_wallet: input.creator_wallet,
      bounty_amount: input.bounty_amount,
      condition: input.condition,
      game: input.game || 'VAULT',
    }),
  });
  return handleResponse<Challenge>(res);
}

export async function acceptChallenge(id: string, challengerWallet: string): Promise<Challenge> {
  const res = await fetch(`${API_BASE}/${id}/accept`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      challenger_wallet: challengerWallet,
    }),
  });
  return handleResponse<Challenge>(res);
}

export async function claimBounty(id: string, claimerWallet: string): Promise<Challenge> {
  const res = await fetch(`${API_BASE}/${id}/claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      claimer_wallet: claimerWallet,
    }),
  });
  return handleResponse<Challenge>(res);
}

export async function fetchChallengeByMatch(matchId: string): Promise<Challenge | null> {
  try {
    const res = await fetch(`${API_BASE}/by-match/${matchId}`);
    if (res.status === 404 || !res.ok) return null;
    const data = await res.json();
    return data as Challenge;
  } catch {
    return null;
  }
}

