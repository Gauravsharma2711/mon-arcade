import { useState, useEffect, useCallback, useRef } from 'react';
import { bluffApi, BluffMatchClientView } from '../lib/bluffApi';

export type LobbyStatus =
  | 'IDLE'
  | 'CONNECTING...'
  | 'CREATING DUEL...'
  | 'WAITING FOR OPPONENT...'
  | 'JOINING...'
  | 'READY'
  | 'ERROR';

/**
 * Returns a persistent mock/local player address for testing and arcade play.
 */
export function getOrCreatePlayerId(): string {
  if (typeof window === 'undefined') return '0xarcade_player_1';
  const stored = localStorage.getItem('mon_arcade_bluff_player_id');
  if (stored) return stored;

  // Generate deterministic-looking 0x address
  const randomHex = Array.from({ length: 8 }, () =>
    Math.floor(Math.random() * 16).toString(16)
  ).join('');
  const newId = `0x71a${randomHex}9b2`;
  localStorage.setItem('mon_arcade_bluff_player_id', newId);
  return newId;
}

export function useBluffLobby() {
  const [playerId, setPlayerId] = useState<string>(getOrCreatePlayerId);
  const [openLobbies, setOpenLobbies] = useState<BluffMatchClientView[]>([]);
  const [createdMatch, setCreatedMatch] = useState<BluffMatchClientView | null>(null);
  const [status, setStatus] = useState<LobbyStatus>('CONNECTING...');
  const [error, setError] = useState<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Switch or reset player identity (e.g. to test Player 2 vs Player 1 in same browser)
  const switchPlayer = useCallback((newId: string) => {
    localStorage.setItem('mon_arcade_bluff_player_id', newId);
    setPlayerId(newId);
  }, []);

  // Fetch open lobbies
  const fetchLobbies = useCallback(async () => {
    try {
      setError(null);
      const lobbies = await bluffApi.getOpenLobbies();
      setOpenLobbies(lobbies);
      setStatus((prev) => (prev === 'CONNECTING...' ? 'IDLE' : prev));
    } catch (err: any) {
      setError(err.message || 'Failed to connect to arcade server');
      setStatus('ERROR');
    }
  }, []);

  // Initial lobby load
  useEffect(() => {
    fetchLobbies();
  }, [fetchLobbies]);

  // Poll created match when waiting for opponent
  useEffect(() => {
    if (!createdMatch || createdMatch.status !== 'WAITING') {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      return;
    }

    setStatus('WAITING FOR OPPONENT...');

    const poll = async () => {
      try {
        const latest = await bluffApi.getMatch(createdMatch.id, playerId);
        setCreatedMatch(latest);

        // If opponent entered, duel is ready!
        if (latest.status !== 'WAITING' || latest.opponent) {
          setStatus('READY');
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
        }
      } catch (err: any) {
        // Continue polling unless match is gone
      }
    };

    pollTimerRef.current = setInterval(poll, 1500);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [createdMatch?.id, createdMatch?.status, playerId]);

  // Create a new duel
  const createDuel = useCallback(
    async (stakeAmount: number, secretValue: number): Promise<BluffMatchClientView> => {
      try {
        setError(null);
        setStatus('CREATING DUEL...');
        const match = await bluffApi.createMatch({
          creator_id: playerId,
          stake_amount: stakeAmount,
          secret_value: secretValue,
          turn_seconds: 15,
        });
        setCreatedMatch(match);
        setStatus('WAITING FOR OPPONENT...');
        await fetchLobbies();
        return match;
      } catch (err: any) {
        setError(err.message || 'Failed to create duel');
        setStatus('ERROR');
        throw err;
      }
    },
    [playerId, fetchLobbies]
  );

  // Join an existing duel
  const joinDuel = useCallback(
    async (matchId: string, secretValue: number): Promise<BluffMatchClientView> => {
      try {
        setError(null);
        setStatus('JOINING...');
        const match = await bluffApi.joinMatch(matchId, {
          player_id: playerId,
          secret_value: secretValue,
        });
        setStatus('READY');
        return match;
      } catch (err: any) {
        setError(err.message || 'Failed to join duel');
        setStatus('ERROR');
        throw err;
      }
    },
    [playerId]
  );

  // Cancel created duel
  const cancelDuel = useCallback(
    async (matchId: string): Promise<void> => {
      try {
        setError(null);
        await bluffApi.cancelMatch(matchId, playerId);
        setCreatedMatch(null);
        setStatus('IDLE');
        await fetchLobbies();
      } catch (err: any) {
        setError(err.message || 'Failed to cancel duel');
      }
    },
    [playerId, fetchLobbies]
  );

  // Spawn a simulated challenger for local single-browser playtesting
  const spawnSimulatedOpponent = useCallback(
    async (matchId: string): Promise<BluffMatchClientView> => {
      try {
        setError(null);
        setStatus('JOINING...');
        const randomSecret = Math.floor(Math.random() * 10) + 1;
        const simulatedId = `0xsimulated_duelist_${Math.floor(Math.random() * 1000)}`;
        const match = await bluffApi.joinMatch(matchId, {
          player_id: simulatedId,
          secret_value: randomSecret,
        });
        setCreatedMatch(match);
        setStatus('READY');
        return match;
      } catch (err: any) {
        setError(err.message || 'Failed to spawn simulated opponent');
        throw err;
      }
    },
    []
  );

  return {
    playerId,
    switchPlayer,
    openLobbies,
    createdMatch,
    status,
    error,
    refreshLobbies: fetchLobbies,
    createDuel,
    joinDuel,
    spawnSimulatedOpponent,
    cancelDuel,
    clearCreatedMatch: () => setCreatedMatch(null),
  };
}
