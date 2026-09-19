/**
 * Mon Arcade — First Blood / Early Arcade Player API Client
 */

export interface FirstBloodRecord {
  wallet: string;
  first_participation_at: string;
  player_number?: number | null;
  first_game: string;
  is_first_time: boolean;
}

const API_BASE = '/api/first-blood';

export async function recordFirstBlood(
  wallet: string,
  game: 'VAULT' | 'BLUFF' = 'VAULT'
): Promise<FirstBloodRecord> {
  const res = await fetch(`${API_BASE}/record`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet, game }),
  });
  if (!res.ok) {
    throw new Error(`Failed to record first blood (${res.status})`);
  }
  return res.json() as Promise<FirstBloodRecord>;
}

export async function getFirstBlood(wallet: string): Promise<FirstBloodRecord | null> {
  try {
    const res = await fetch(`${API_BASE}/${wallet}`);
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return res.json() as Promise<FirstBloodRecord>;
  } catch {
    return null;
  }
}
