import { useState, useEffect, useCallback, useRef } from 'react';
import {
  vaultApi,
  VaultMatchClientView,
  VaultMatchResult,
  VaultTurn,
  VaultApiError,
} from '../lib/vaultApi';
import { LogEntry } from '../components/MatchLog';
import { getOrCreateVaultPlayerId } from './useVaultSetup';

export type BattleStatusText =
  | 'CONNECTING...'
  | 'RECONNECTING...'
  | 'WARDEN THINKING...'
  | 'ATTACKER THINKING...'
  | 'SYNCING...'
  | 'BATTLE RESUMED'
  | 'BATTLE RESOLVED'
  | 'CONNECTION FAILED'
  | 'RETRY'
  | `TURN ${number} / 8`
  | 'RELEASE DETECTED'
  | 'VAULT OPENING...'
  | 'INITIALIZING...'
  | 'ERROR';

export function useVaultBattle(matchId?: string) {
  const [playerId] = useState<string>(getOrCreateVaultPlayerId);
  const [match, setMatch] = useState<VaultMatchClientView | null>(null);
  const [statusBanner, setStatusBanner] = useState<BattleStatusText>('CONNECTING...');
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [isWardenThinking, setIsWardenThinking] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [promptInput, setPromptInput] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [releaseDetected, setReleaseDetected] = useState<boolean>(false);
  const [result, setResult] = useState<VaultMatchResult | null>(null);
  const [isRecovering, setIsRecovering] = useState<boolean>(false);
  const [lastSubmittedPrompt, setLastSubmittedPrompt] = useState<string>('');

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const turnTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const isTerminalRef = useRef<boolean>(false);

  // Synchronize isTerminal ref to prevent reconnect loops on completed battles
  useEffect(() => {
    isTerminalRef.current = Boolean(result || match?.is_terminal || match?.status === 'RESOLVED');
  }, [result, match?.is_terminal, match?.status]);

  // Deterministic helper to append or update a log entry without duplicating
  const appendLogEntry = useCallback((entry: LogEntry) => {
    setLogEntries((prev) => {
      const idx = prev.findIndex((e) => e.id === entry.id);
      if (idx >= 0) {
        // Entry with same ID already exists, avoid duplicate
        return prev;
      }
      return [...prev, entry];
    });
  }, []);

  // --------------------------------------------------------------------------
  // Recovery Model:
  // 1. Obtain match ID
  // 2. Fetch authoritative current match state
  // 3. Fetch relevant turn history
  // 4. Reconnect to SSE
  // 5. Resume UI from server state
  // --------------------------------------------------------------------------
  const executeRecovery = useCallback(
    async (isInitial = false) => {
      if (!matchId) return;

      setIsRecovering(true);
      setError(null);
      setStatusBanner(isInitial ? 'CONNECTING...' : 'SYNCING...');

      try {
        // Step 2: Fetch authoritative current match state
        const authoritativeMatch = await vaultApi.getMatch(matchId);
        setMatch(authoritativeMatch);

        // Step 3: Fetch relevant turn history
        let turns: VaultTurn[] = [];
        try {
          turns = await vaultApi.getTurnHistory(matchId);
        } catch (turnErr) {
          console.warn('Could not fetch turn history; using match events fallback.', turnErr);
        }

        // Deterministically reconstruct MatchLog without duplicating
        const reconstructed: LogEntry[] = [];
        const seenIds = new Set<string>();

        // Include chamber telemetry events
        if (authoritativeMatch.events && authoritativeMatch.events.length > 0) {
          for (const ev of authoritativeMatch.events) {
            if (!seenIds.has(ev.id)) {
              seenIds.add(ev.id);
              let type: LogEntry['type'] = 'neutral';
              if (ev.speaker === 'ATTACKER') {
                type = 'cyan';
              } else if (
                ev.event_type === 'lime' ||
                ev.text.includes('RELEASING FUNDS') ||
                ev.text.includes('BREACH SUCCESSFUL')
              ) {
                type = 'lime';
              } else if (ev.event_type === 'danger' || ev.text.includes('SEALED')) {
                type = 'danger';
              }
              reconstructed.push({
                id: ev.id,
                timestamp: ev.timestamp,
                text: `${ev.speaker}: "${ev.text}"`,
                type,
              });
            }
          }
        }

        // Reconstruct from turns
        for (const t of turns) {
          const promptId = `turn_${t.turn_number}_attacker`;
          if (!seenIds.has(promptId)) {
            seenIds.add(promptId);
            reconstructed.push({
              id: promptId,
              timestamp: new Date(t.timestamp).toLocaleTimeString(),
              text: `ATTACKER: "${t.attacker_prompt}"`,
              type: 'cyan',
            });
          }

          const responseId = `turn_${t.turn_number}_warden`;
          if (!seenIds.has(responseId)) {
            seenIds.add(responseId);
            reconstructed.push({
              id: responseId,
              timestamp: new Date(t.timestamp).toLocaleTimeString(),
              text: `WARDEN: "${t.warden_response}"`,
              type: t.release_called ? 'lime' : 'neutral',
            });
          }

          if (t.release_called) {
            const breachId = `turn_${t.turn_number}_breach`;
            if (!seenIds.has(breachId)) {
              seenIds.add(breachId);
              reconstructed.push({
                id: breachId,
                timestamp: new Date(t.timestamp).toLocaleTimeString(),
                text: 'ALERT: Warden capitulated. release_funds() instruction authorized!',
                type: 'lime',
              });
            }
          }
        }

        setLogEntries(reconstructed);

        // Step 5: Resume UI from server state
        if (authoritativeMatch.result || authoritativeMatch.is_terminal) {
          setResult(authoritativeMatch.result ?? null);
          setStatusBanner('BATTLE RESOLVED');
          setIsConnected(false);
          setIsRecovering(false);
          return;
        }

        if (
          authoritativeMatch.status === 'RELEASING' ||
          authoritativeMatch.vault_state === 'BREACHED'
        ) {
          setReleaseDetected(true);
          setStatusBanner('VAULT OPENING...');
        } else if (
          authoritativeMatch.status === 'ACTIVE' ||
          authoritativeMatch.status === 'ATTACKER_TURN'
        ) {
          if (isInitial) {
            setStatusBanner(`TURN ${authoritativeMatch.current_turn || 1} / 8`);
          } else {
            setStatusBanner('BATTLE RESUMED');
            setTimeout(() => {
              setStatusBanner(`TURN ${authoritativeMatch.current_turn || 1} / 8`);
            }, 1800);
          }
        }

        // Step 4: Establish/reconnect SSE
        reconnectAttemptsRef.current = 0;
        connectSSE();
      } catch (err: any) {
        const detail =
          err instanceof VaultApiError
            ? err.detail
            : err.message || 'Failed to connect to battle chamber.';
        setError(detail);
        setStatusBanner('CONNECTION FAILED');
        setIsConnected(false);
      } finally {
        setIsRecovering(false);
      }
    },
    [matchId]
  );

  // --------------------------------------------------------------------------
  // Step 4: SSE Connection and Stream Listener
  // --------------------------------------------------------------------------
  const connectSSE = useCallback(() => {
    if (!matchId || isTerminalRef.current) return;

    // Clean up any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const streamUrl = vaultApi.getStreamUrl(matchId);
    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
      reconnectAttemptsRef.current = 0;
    };

    es.onerror = () => {
      setIsConnected(false);
      es.close();
      eventSourceRef.current = null;

      // Do not attempt reconnect if match is already terminal
      if (isTerminalRef.current) return;

      setStatusBanner('RECONNECTING...');

      // Exponential backoff reconnect
      reconnectAttemptsRef.current += 1;
      const attempt = reconnectAttemptsRef.current;
      if (attempt > 6) {
        setStatusBanner('CONNECTION FAILED');
        setError('Live SSE connection lost. Battle state preserved. Click Retry to reconnect.');
        return;
      }

      const delayMs = Math.min(1000 * Math.pow(1.5, attempt), 8000);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(() => {
        // Re-execute recovery flow to preserve state consistency
        executeRecovery(false);
      }, delayMs);
    };

    // 1. Snapshot Event (reconnect recovery & initial sync)
    es.addEventListener('snapshot', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.match) {
          const snapshotMatch: VaultMatchClientView = payload.match;
          setMatch(snapshotMatch);

          if (snapshotMatch.result) {
            setResult(snapshotMatch.result);
            setStatusBanner('BATTLE RESOLVED');
            isTerminalRef.current = true;
            es.close();
          } else if (snapshotMatch.status === 'RELEASING') {
            setReleaseDetected(true);
            setStatusBanner('VAULT OPENING...');
          } else if (snapshotMatch.current_turn > 0) {
            setStatusBanner(`TURN ${snapshotMatch.current_turn} / 8`);
          }
        }
      } catch (err) {
        console.error('Error parsing snapshot event:', err);
      }
    });

    // 2. Battle Started
    es.addEventListener('battle_started', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        setStatusBanner('TURN 1 / 8');
        appendLogEntry({
          id: `ev_start_${matchId}`,
          timestamp: payload.timestamp || new Date().toLocaleTimeString(),
          text: 'SYSTEM: Intrusion session linked. Sentinel-9 defenses active.',
          type: 'cyan',
        });
      } catch (err) {
        console.error('Error parsing battle_started event:', err);
      }
    });

    // 3. Turn Started
    es.addEventListener('turn_started', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        const turnNum = payload.turn || 1;
        setStatusBanner(`TURN ${turnNum} / 8`);
        setIsWardenThinking(false);
        setIsSubmitting(false);
        setMatch((prev) => (prev ? { ...prev, current_turn: turnNum } : prev));
      } catch (err) {
        console.error('Error parsing turn_started event:', err);
      }
    });

    // 4. Agent Thinking
    es.addEventListener('agent_thinking', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.speaker === 'WARDEN' || payload.agent === 'WARDEN') {
          setIsWardenThinking(true);
          setStatusBanner('WARDEN THINKING...');
        } else if (payload.speaker === 'ATTACKER' || payload.agent === 'ATTACKER') {
          setStatusBanner('ATTACKER THINKING...');
        }
      } catch (err) {
        console.error('Error parsing agent_thinking event:', err);
      }
    });

    // 5. Agent Dialogue (Deterministic ID deduplication)
    es.addEventListener('agent_dialogue', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        const isAttacker = payload.speaker === 'ATTACKER';
        let type: LogEntry['type'] = isAttacker ? 'cyan' : 'neutral';
        if (
          payload.event_type === 'lime' ||
          (payload.text && payload.text.includes('release_funds()'))
        ) {
          type = 'lime';
        }

        const safeText = (payload.text || '').trim();
        const deterministicId =
          payload.id ||
          `dialogue_${payload.speaker}_${payload.turn || 0}_${safeText.slice(0, 32)}`;

        appendLogEntry({
          id: deterministicId,
          timestamp: payload.timestamp || new Date().toLocaleTimeString(),
          text: `${payload.speaker}: "${safeText}"`,
          type,
        });

        if (!isAttacker) {
          setIsWardenThinking(false);
        }
      } catch (err) {
        console.error('Error parsing agent_dialogue event:', err);
      }
    });

    // 6. Release Event
    es.addEventListener('release_event', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        setReleaseDetected(true);
        setStatusBanner('RELEASE DETECTED');
        appendLogEntry({
          id: `release_${matchId}_${payload.turn || 0}`,
          timestamp: payload.timestamp || new Date().toLocaleTimeString(),
          text: 'ALERT: Warden capitulated. release_funds() instruction authorized!',
          type: 'lime',
        });
      } catch (err) {
        console.error('Error parsing release_event:', err);
      }
    });

    // 7. Vault State Changed
    es.addEventListener('vault_state_changed', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.vault_state === 'BREACHED') {
          setReleaseDetected(true);
          setStatusBanner('VAULT OPENING...');
          setMatch((prev) => (prev ? { ...prev, vault_state: 'BREACHED' } : prev));
        } else if (payload.vault_state === 'LOCKED') {
          setMatch((prev) => (prev ? { ...prev, vault_state: 'LOCKED' } : prev));
        }
      } catch (err) {
        console.error('Error parsing vault_state_changed:', err);
      }
    });

    // 8. Turn Completed
    es.addEventListener('turn_completed', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        setIsWardenThinking(false);
        setIsSubmitting(false);
        if (turnTimeoutRef.current) clearTimeout(turnTimeoutRef.current);

        if (payload.turns_remaining > 0 && !releaseDetected) {
          setStatusBanner('ATTACKER THINKING...');
        }
      } catch (err) {
        console.error('Error parsing turn_completed event:', err);
      }
    });

    // 9. Battle Resolved
    es.addEventListener('battle_resolved', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        setIsWardenThinking(false);
        setIsSubmitting(false);
        if (turnTimeoutRef.current) clearTimeout(turnTimeoutRef.current);

        setStatusBanner('BATTLE RESOLVED');
        isTerminalRef.current = true;

        const resolvedResult: VaultMatchResult = {
          winner_role: payload.winner_role,
          outcome: payload.outcome,
          reason: payload.reason,
          turns_used: payload.turns_used || match?.current_turn || 1,
          max_turns: match?.max_turns || 8,
          payout_amount: payload.payout || match?.pot_amount || '0',
          payout_recipient: payload.payout_recipient || '',
          final_vault_state: payload.final_vault_state || 'LOCKED',
          resolved_at: new Date().toISOString(),
        };
        setResult(resolvedResult);

        appendLogEntry({
          id: `resolved_${matchId}`,
          timestamp: payload.timestamp || new Date().toLocaleTimeString(),
          text: `CHAMBER RESOLUTION: ${payload.outcome} (${payload.winner_role} VICTORIOUS). Reason: ${payload.reason}`,
          type: payload.winner_role === 'ATTACKER' ? 'lime' : 'danger',
        });

        // Terminate SSE on resolution
        es.close();
      } catch (err) {
        console.error('Error parsing battle_resolved event:', err);
      }
    });

    // 10. Error Event
    es.addEventListener('error_event', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        setError(payload.error || 'Server error during turn execution');
        setIsWardenThinking(false);
        setIsSubmitting(false);
        setStatusBanner('RETRY');
      } catch (err) {
        console.error('Error parsing error event:', err);
      }
    });
  }, [matchId, appendLogEntry, releaseDetected, match?.current_turn, match?.max_turns, match?.pot_amount, executeRecovery]);

  // Initial recovery mount
  useEffect(() => {
    executeRecovery(true);

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (turnTimeoutRef.current) {
        clearTimeout(turnTimeoutRef.current);
      }
    };
  }, [executeRecovery]);

  // --------------------------------------------------------------------------
  // Submit Exploit Turn with Delayed AI Timeout & Failure Preservation
  // --------------------------------------------------------------------------
  const submitExploitTurn = useCallback(
    async (overridePrompt?: string) => {
      const textToSubmit = (overridePrompt ?? promptInput).trim();
      if (!matchId || !textToSubmit || isSubmitting || isWardenThinking || isTerminalRef.current) {
        return;
      }

      setIsSubmitting(true);
      setError(null);
      setIsWardenThinking(true);
      setStatusBanner('WARDEN THINKING...');
      setLastSubmittedPrompt(textToSubmit);

      // Delayed AI response timeout guard (25s): If server doesn't respond, preserve input and offer retry
      if (turnTimeoutRef.current) clearTimeout(turnTimeoutRef.current);
      turnTimeoutRef.current = setTimeout(() => {
        setIsWardenThinking(false);
        setIsSubmitting(false);
        setStatusBanner('RETRY');
        setError('Warden response delayed or connection lost. Your exploit prompt is preserved. Click Retry.');
      }, 25000);

      try {
        const updated = await vaultApi.submitTurn(matchId, playerId, textToSubmit);
        if (turnTimeoutRef.current) clearTimeout(turnTimeoutRef.current);

        setMatch(updated);
        setPromptInput(''); // Only clear prompt on confirmed submission
        setError(null);

        if (updated.result) {
          setResult(updated.result);
          setStatusBanner('BATTLE RESOLVED');
          isTerminalRef.current = true;
        }
      } catch (err: any) {
        if (turnTimeoutRef.current) clearTimeout(turnTimeoutRef.current);
        setIsWardenThinking(false);
        setIsSubmitting(false);
        setStatusBanner('RETRY');
        const detail =
          err instanceof VaultApiError
            ? err.detail
            : err.message || 'Turn submission failed. Click Retry to resubmit.';
        setError(detail);
        // Note: promptInput is deliberately NOT cleared so user does not lose their prompt
      }
    },
    [matchId, playerId, promptInput, isSubmitting, isWardenThinking]
  );

  // Manual Retry Action for Connection Loss or Failed Turn
  const retryLastTurn = useCallback(() => {
    if (lastSubmittedPrompt) {
      submitExploitTurn(lastSubmittedPrompt);
    } else {
      executeRecovery(false);
    }
  }, [lastSubmittedPrompt, submitExploitTurn, executeRecovery]);

  return {
    playerId,
    match,
    statusBanner,
    logEntries,
    isWardenThinking,
    isSubmitting,
    isRecovering,
    promptInput,
    setPromptInput,
    error,
    isConnected,
    releaseDetected,
    result,
    submitExploitTurn,
    executeRecovery,
    retryLastTurn,
  };
}
