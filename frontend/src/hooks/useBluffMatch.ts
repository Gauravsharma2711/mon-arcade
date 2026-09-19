import { useState, useEffect, useCallback, useRef } from 'react';
import {
  bluffApi,
  BluffMatchClientView,
  BluffApiError,
  BluffActionAvailable,
} from '../lib/bluffApi';
import { getOrCreatePlayerId } from './useBluffLobby';

export type BluffUIState =
  | 'WAITING'
  | 'CONNECTING'
  | 'CONFIRMING'
  | 'ACTIVE'
  | 'REVEALING'
  | 'SUCCESS'
  | 'FAILED'
  | 'RETRY';

export type ConnectionStatus = 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED';

export interface BluffDetailedError {
  message: string;
  isMatchAlive: boolean;
  actionAvailable: BluffActionAvailable;
  canRetry: boolean;
  statusCode?: number;
}

export function useBluffMatch(matchId: string) {
  const [playerId] = useState<string>(getOrCreatePlayerId);
  const [match, setMatch] = useState<BluffMatchClientView | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<BluffDetailedError | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('CONNECTED');

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const consecutiveFailuresRef = useRef<number>(0);

  // Derive meaningful UI state authoritatively from server match state and operation lifecycle
  const deriveUIState = (
    currentMatch: BluffMatchClientView | null,
    submitting: boolean,
    err: BluffDetailedError | null,
    initialLoading: boolean
  ): BluffUIState => {
    if (err && (!currentMatch || !err.isMatchAlive)) {
      return err.canRetry ? 'RETRY' : 'FAILED';
    }
    if (initialLoading && !currentMatch) {
      return 'CONNECTING';
    }
    if (submitting) {
      return 'CONFIRMING';
    }
    if (!currentMatch) {
      return 'CONNECTING';
    }

    switch (currentMatch.status) {
      case 'WAITING':
        return 'WAITING';
      case 'ACTIVE':
        return 'ACTIVE';
      case 'DECISION':
        return 'ACTIVE';
      case 'REVEALING':
        return 'REVEALING';
      case 'RESOLVED':
        return 'SUCCESS';
      case 'CANCELLED':
        return 'FAILED';
      default:
        return 'ACTIVE';
    }
  };

  // Convert caught error into structured BluffDetailedError
  const parseError = (err: any): BluffDetailedError => {
    if (err instanceof BluffApiError) {
      return {
        message: err.message,
        isMatchAlive: err.isMatchAlive,
        actionAvailable: err.actionAvailable,
        canRetry: err.actionAvailable === 'RETRY' || err.status === 0 || err.status >= 500,
        statusCode: err.status,
      };
    }
    return {
      message: err?.message || 'A network error occurred while communicating with the engine.',
      isMatchAlive: true,
      actionAvailable: 'RETRY',
      canRetry: true,
      statusCode: 0,
    };
  };

  // Fetch authoritative state from backend
  const fetchState = useCallback(async () => {
    if (!matchId) return;
    try {
      const data = await bluffApi.getMatch(matchId, playerId);
      setMatch(data);
      setError(null);
      consecutiveFailuresRef.current = 0;
      setConnectionStatus('CONNECTED');
    } catch (err: any) {
      const parsed = parseError(err);
      setError(parsed);
      consecutiveFailuresRef.current += 1;
      if (consecutiveFailuresRef.current >= 3) {
        setConnectionStatus('DISCONNECTED');
      } else {
        setConnectionStatus('RECONNECTING');
      }
    } finally {
      setIsLoading(false);
    }
  }, [matchId, playerId]);

  // Initial load and auto-polling
  useEffect(() => {
    setIsLoading(true);
    fetchState();

    const poll = async () => {
      try {
        const latest = await bluffApi.getMatch(matchId, playerId);
        setMatch(latest);
        consecutiveFailuresRef.current = 0;
        setConnectionStatus('CONNECTED');

        // Stop polling if match is resolved or cancelled
        if (latest.status === 'RESOLVED' || latest.status === 'CANCELLED') {
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
        }
      } catch (err: any) {
        consecutiveFailuresRef.current += 1;
        if (consecutiveFailuresRef.current >= 3) {
          setConnectionStatus('DISCONNECTED');
        } else {
          setConnectionStatus('RECONNECTING');
        }
        // Do not overwrite match state on transient poll failure
      }
    };

    pollTimerRef.current = setInterval(poll, 1500);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [matchId, playerId, fetchState]);

  // Submit PUSH or FOLD decision
  const submitDecision = useCallback(
    async (action: 'PUSH' | 'FOLD') => {
      if (!matchId) return;
      try {
        setIsSubmitting(true);
        setError(null);
        const resolved = await bluffApi.submitDecision(matchId, {
          player_id: playerId,
          action,
        });
        setMatch(resolved);
        return resolved;
      } catch (err: any) {
        const parsed = parseError(err);
        setError(parsed);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [matchId, playerId]
  );

  // Submit secret value commitment
  const commitSecret = useCallback(
    async (secretValue: number) => {
      if (!matchId) return;
      try {
        setIsSubmitting(true);
        setError(null);
        const updated = await bluffApi.commitSecret(matchId, {
          player_id: playerId,
          secret_value: secretValue,
        });
        setMatch(updated);
        return updated;
      } catch (err: any) {
        const parsed = parseError(err);
        setError(parsed);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [matchId, playerId]
  );

  // Join open duel as opponent
  const joinDuel = useCallback(
    async (secretValue: number): Promise<BluffMatchClientView> => {
      if (!matchId) throw new Error('No match ID');
      try {
        setIsSubmitting(true);
        setError(null);
        const updated = await bluffApi.joinMatch(matchId, {
          player_id: playerId,
          secret_value: secretValue,
        });
        setMatch(updated);
        return updated;
      } catch (err: any) {
        const parsed = parseError(err);
        setError(parsed);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [matchId, playerId]
  );

  // Spawn simulated bot opponent for creator
  const spawnBot = useCallback(
    async (): Promise<BluffMatchClientView> => {
      if (!matchId) throw new Error('No match ID');
      try {
        setIsSubmitting(true);
        setError(null);
        const randomSecret = Math.floor(Math.random() * 10) + 1;
        const simulatedId = `0xsimulated_duelist_${Math.floor(Math.random() * 1000)}`;
        const updated = await bluffApi.joinMatch(matchId, {
          player_id: simulatedId,
          secret_value: randomSecret,
        });
        setMatch(updated);
        return updated;
      } catch (err: any) {
        const parsed = parseError(err);
        setError(parsed);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [matchId]
  );

  // Cancel match for creator
  const cancelMatch = useCallback(
    async (): Promise<BluffMatchClientView> => {
      if (!matchId) throw new Error('No match ID');
      try {
        setIsSubmitting(true);
        setError(null);
        const updated = await bluffApi.cancelMatch(matchId, playerId);
        setMatch(updated);
        return updated;
      } catch (err: any) {
        const parsed = parseError(err);
        setError(parsed);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [matchId, playerId]
  );

  const uiState = deriveUIState(match, isSubmitting, error, isLoading);

  return {
    playerId,
    match,
    uiState,
    connectionStatus,
    isLoading,
    isSubmitting,
    error,
    refresh: fetchState,
    submitDecision,
    commitSecret,
    joinDuel,
    spawnBot,
    cancelMatch,
    clearError: () => setError(null),
  };
}

