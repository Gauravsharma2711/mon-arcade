import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { PageContainer } from '../../components/PageContainer';
import { Panel } from '../../components/Panel';
import { Hud } from '../../components/Hud';
import { ArcadeButton } from '../../components/ArcadeButton';
import { LoadingState } from '../../components/LoadingState';
import { LocalizedTurnTimer } from './LocalizedTurnTimer';
import { useBluffMatch } from '../../hooks/useBluffMatch';
import { bluffApi } from '../../lib/bluffApi';
import {
  EyeOff,
  Shield,
  Swords,
  AlertCircle,
  CheckCircle2,
  Copy,
  Check,
  ArrowRight,
  ArrowLeft,
  Flame,
  Flag,
  HelpCircle,
  RefreshCw,
  WifiOff,
  X,
  Bot,
  Lock,
} from 'lucide-react';

export const BluffMatchPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const matchId = id || '';
  const navigate = useNavigate();

  const {
    playerId,
    match,
    uiState,
    connectionStatus,
    isLoading,
    isSubmitting,
    error,
    refresh,
    submitDecision,
    commitSecret,
    joinDuel,
    spawnBot,
    cancelMatch,
    clearError,
  } = useBluffMatch(matchId);

  const [selectedCommitValue, setSelectedCommitValue] = useState<number>(7);
  const [copiedId, setCopiedId] = useState<boolean>(false);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);
  const [slowLoadWarning, setSlowLoadWarning] = useState<boolean>(false);

  // Monitor loading latency for cold-start cloud instances (Render spin-up)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isLoading && !match) {
        setSlowLoadWarning(true);
      }
    }, 4000);
    return () => clearTimeout(timer);
  }, [isLoading, match]);

  // Copy Match ID helper
  const handleCopyId = () => {
    if (!matchId) return;
    navigator.clipboard.writeText(matchId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Copy Duel Share Link helper
  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  // Copy Hash helper
  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  // 1. Initial Loading / Connecting State
  if (isLoading && !match) {
    return (
      <PageContainer maxWidth="md" className="py-12 space-y-4">
        <LoadingState
          status="CONNECTING"
          message={
            slowLoadWarning
              ? 'WAKING GAME ENGINE (CLOUD SERVICE WAKING UP)...'
              : 'CONNECTING TO AUTHORITATIVE MATCH ENGINE...'
          }
          subtext={
            slowLoadWarning
              ? 'Render cloud instances may take 20-40s to warm up. Your match state is safe.'
              : 'RETRIEVING AUTHORITATIVE GAME STATE'
          }
        />
        {slowLoadWarning && (
          <div className="flex justify-center pt-2">
            <ArcadeButton variant="secondary" size="sm" onClick={() => refresh()}>
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              RETRY CONNECTION NOW
            </ArcadeButton>
          </div>
        )}
      </PageContainer>
    );
  }

  // 2. Fatal Failure / Not Found / Already Closed State (when no match in memory)
  if (error && !match) {
    return (
      <PageContainer maxWidth="md" className="py-10 space-y-6">
        <Panel header="ENGINE RECOVERY & ERROR STATUS" accent="danger">
          <div className="py-6 text-center space-y-4">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-arcade-danger/10 border border-arcade-danger/40 text-arcade-danger">
              <AlertCircle className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <h2 className="font-display text-lg text-arcade-text tracking-wide uppercase">
                {error.statusCode === 404
                  ? 'DUEL NOT FOUND ON SERVER'
                  : error.statusCode === 410
                  ? 'DUEL ALREADY CONCLUDED'
                  : 'FAILED TO COMMUNICATE WITH ENGINE'}
              </h2>
              <p className="text-xs font-mono text-arcade-danger max-w-md mx-auto">
                {error.message}
              </p>
            </div>

            {/* Context: Whether the match is still alive */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded bg-arcade-bg border border-arcade-border text-xs font-mono">
              <span className="text-arcade-subtle uppercase">MATCH STATUS:</span>
              <span
                className={`font-bold ${
                  error.isMatchAlive ? 'text-arcade-lime' : 'text-arcade-danger'
                }`}
              >
                {error.isMatchAlive
                  ? 'MATCH ALIVE ON SERVER'
                  : 'MATCH CLOSED / EXPIRED'}
              </span>
            </div>

            {/* Context: What action is available */}
            <div className="flex flex-wrap items-center justify-center gap-3 pt-3">
              {error.actionAvailable === 'VIEW_RESULT' && (
                <Link to={`/bluff/${matchId}/result`}>
                  <ArcadeButton variant="primary" size="md">
                    VIEW SHOWDOWN RESULT
                    <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </ArcadeButton>
                </Link>
              )}

              {error.canRetry && (
                <ArcadeButton variant="secondary" size="md" onClick={() => refresh()}>
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                  RETRY CONNECTION
                </ArcadeButton>
              )}

              <Link to="/bluff">
                <ArcadeButton variant="pink" size="md">
                  <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
                  RETURN TO LOBBY
                </ArcadeButton>
              </Link>
            </div>
          </div>
        </Panel>
      </PageContainer>
    );
  }

  if (!match) {
    return (
      <PageContainer maxWidth="md" className="py-12 space-y-4">
        <LoadingState
          status="CONNECTING"
          message="INITIALIZING BLUFF DUEL..."
          subtext="SYNCHRONIZING AUTHORITATIVE MATCH STATE"
        />
      </PageContainer>
    );
  }

  // Resolve player and opponent views
  const isCreator = Boolean(match.creator?.player_id && match.creator.player_id === playerId);
  const isSeatOpen = match.status === 'WAITING' && match.opponent === null;
  const myPlayer = isCreator ? match.creator : match.opponent;
  const opponentPlayer = isCreator ? match.opponent : match.creator;
  const isBotOpponent = Boolean(opponentPlayer?.player_id?.startsWith('0xsimulated'));
  const isSpectator = !isCreator && match.opponent !== null && match.opponent?.player_id !== playerId && !isBotOpponent;
  const isPlayerTurn =
    (match.can_act && match.active_turn_player_id === playerId) ||
    (match.status === 'DECISION' && isBotOpponent);
  const isOpponentTurn =
    match.status === 'DECISION' &&
    match.active_turn_player_id &&
    match.active_turn_player_id !== playerId &&
    !isBotOpponent;

  // Has my player already submitted action?
  const myAction = myPlayer?.action;

  // Revealed values for final showdown
  const creatorRevealed = match.result?.creator_revealed;
  const opponentRevealed = match.result?.opponent_revealed;

  const myRevealedValue = isCreator
    ? creatorRevealed?.secret_value ?? myPlayer?.secret_value
    : opponentRevealed?.secret_value ?? myPlayer?.secret_value;

  const theirRevealedValue = isCreator
    ? opponentRevealed?.secret_value ?? opponentPlayer?.secret_value
    : creatorRevealed?.secret_value ?? opponentPlayer?.secret_value;

  // Automated action for local simulated playtesting bot
  useEffect(() => {
    if (!match || match.status !== 'DECISION') return;
    if (!opponentPlayer?.player_id?.startsWith('0xsimulated')) return;

    // If bot explicitly holds turn, act after 1.5s. If human holds turn, give 8s before bot acts
    const delay = match.active_turn_player_id === opponentPlayer.player_id ? 1500 : 8000;
    const timer = setTimeout(async () => {
      try {
        const botAction: 'PUSH' | 'FOLD' = Math.random() > 0.35 ? 'PUSH' : 'FOLD';
        await bluffApi.submitDecision(match.id, {
          player_id: opponentPlayer.player_id,
          action: botAction,
        });
        refresh();
      } catch {
        // Silently handled on server
      }
    }, delay);

    return () => clearTimeout(timer);
  }, [match?.id, match?.status, match?.active_turn_player_id, opponentPlayer?.player_id, refresh]);

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* Reconnection Banner if connection interrupted */}
      {connectionStatus !== 'CONNECTED' && (
        <div className="p-3 rounded bg-arcade-warning/15 border border-arcade-warning text-xs font-mono flex items-center justify-between gap-2 shadow-arcade-panel">
          <div className="flex items-center gap-2 text-arcade-warning">
            <WifiOff className="w-4 h-4 shrink-0 animate-pulse motion-reduce:animate-none" />
            <span>
              {connectionStatus === 'RECONNECTING'
                ? 'CONNECTION HITCH: Re-establishing link to engine... State is preserved.'
                : 'ENGINE UNREACHABLE: Network disconnected. Match state remains safe on server.'}
            </span>
          </div>
          <ArcadeButton variant="secondary" size="sm" onClick={() => refresh()}>
            <RefreshCw className="w-3 h-3 mr-1" />
            RETRY
          </ArcadeButton>
        </div>
      )}

      {/* In-Game Non-Fatal Error Toast (e.g. Duplicate Action, Out of Turn Action) */}
      {error && (
        <div className="p-3 rounded bg-arcade-danger/10 border border-arcade-danger/50 text-xs font-mono flex items-start justify-between gap-2">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-arcade-danger shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <div className="font-bold text-arcade-danger uppercase">ACTION REJECTED BY SERVER</div>
              <div className="text-arcade-text">{error.message}</div>
              <div className="text-[11px] text-arcade-subtle">
                Match is active &bull; Action available: <span className="text-arcade-lime font-bold">{error.actionAvailable}</span>
              </div>
            </div>
          </div>
          <button
            onClick={clearError}
            className="p-1 text-arcade-subtle hover:text-arcade-text"
            title="Dismiss error notice"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Top Header & Connection Seam */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-arcade-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-xl text-arcade-pink tracking-wider">
              BLUFF DUEL #{match.id ? match.id.slice(0, 8) : matchId ? matchId.slice(0, 8) : ''}
            </h1>
            <button
              onClick={handleCopyId}
              className="p-1 rounded text-arcade-subtle hover:text-arcade-pink transition-colors"
              title="Copy Duel ID"
              aria-label="Copy Duel ID"
            >
              {copiedId ? <Check className="w-3.5 h-3.5 text-arcade-lime" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
          <p className="text-xs font-mono text-arcade-muted mt-0.5">
            FAST 1V1 DUEL &bull; RECONNECT-RESILIENT AUTHORITATIVE ENGINE
          </p>
        </div>

        {/* Status Badges & Meaningful UI State */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-arcade-subtle bg-arcade-bg px-2.5 py-1 rounded border border-arcade-border">
            <span
              className={`w-2 h-2 rounded-full ${
                connectionStatus === 'CONNECTED'
                  ? 'bg-arcade-lime animate-pulse motion-reduce:animate-none'
                  : 'bg-arcade-warning animate-ping motion-reduce:animate-none'
              }`}
            />
            <span>{connectionStatus === 'CONNECTED' ? 'LIVE' : connectionStatus}</span>
          </div>

          {/* Meaningful UI State Badge */}
          <span
            className={`text-xs font-mono font-bold px-3 py-1 rounded border ${
              uiState === 'SUCCESS'
                ? 'bg-arcade-lime/10 border-arcade-lime/50 text-arcade-lime'
                : uiState === 'CONFIRMING'
                ? 'bg-arcade-warning/15 border-arcade-warning/50 text-arcade-warning'
                : uiState === 'REVEALING'
                ? 'bg-arcade-cyan/15 border-arcade-cyan/50 text-arcade-cyan'
                : uiState === 'ACTIVE'
                ? 'bg-arcade-pink/15 border-arcade-pink/50 text-arcade-pink'
                : 'bg-arcade-panel border-arcade-border text-arcade-muted'
            }`}
          >
            STATE: {uiState}
          </span>
        </div>
      </div>

      {/* Top HUD (Pot, Localized Countdown, Round Info) */}
      <Hud
        leftSlot={
          <div className="font-mono text-xs space-y-0.5">
            <div className="text-[10px] text-arcade-subtle uppercase">STAKES</div>
            <div className="text-arcade-pink font-bold">{match.stake_amount} MON / PLAYER</div>
          </div>
        }
        centerSlot={
          <LocalizedTurnTimer
            initialSeconds={match.seconds_remaining}
            isActive={match.status === 'DECISION'}
            isPlayerTurn={match.can_act}
          />
        }
        rightSlot={
          <div className="font-mono text-xs text-right space-y-0.5">
            <div className="text-[10px] text-arcade-subtle uppercase">TOTAL POT</div>
            <div className="text-arcade-lime font-bold text-sm">{match.pot_amount} MON</div>
          </div>
        }
      />

      {/* 0. CANCELLED STATE NOTICE */}
      {match.status === 'CANCELLED' && (
        <Panel header="DUEL CANCELLED" accent="danger">
          <div className="py-6 text-center space-y-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-arcade-danger/10 border border-arcade-danger/40 text-arcade-danger">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-display text-base text-arcade-text tracking-wide uppercase">
                THIS DUEL WAS CANCELLED
              </h2>
              <p className="text-xs font-mono text-arcade-muted mt-1 max-w-sm mx-auto">
                The match creator cancelled this duel. Any deposited stakes have been refunded.
              </p>
            </div>
            <Link to="/bluff">
              <ArcadeButton variant="pink" size="md">
                <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
                RETURN TO LOBBY
              </ArcadeButton>
            </Link>
          </div>
        </Panel>
      )}

      {/* 1. WAITING FOR OPPONENT (OPPONENT JOIN CHALLENGE VIEW) */}
      {match.status === 'WAITING' && !isCreator && !match.opponent && (
        <Panel header="ACCEPT DUEL CHALLENGE" accent="pink">
          <div className="py-6 text-center space-y-5">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-arcade-pink/15 border border-arcade-pink/50 text-arcade-pink animate-pulse motion-reduce:animate-none shadow-arcade-pink">
              <Swords className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <h2 className="font-display text-lg text-arcade-text tracking-wide uppercase">
                YOU HAVE BEEN CHALLENGED TO A 1V1 DUEL!
              </h2>
              <p className="text-xs font-mono text-arcade-muted max-w-md mx-auto">
                Creator <span className="text-arcade-pink font-bold">{match.creator?.player_id ? `${match.creator.player_id.slice(0, 10)}...` : 'Host'}</span> has staked{' '}
                <span className="text-arcade-pink font-bold">{match.stake_amount} MON</span>. Total pot is{' '}
                <span className="text-arcade-lime font-bold">{match.pot_amount} MON</span>.
              </p>
            </div>

            <div className="max-w-md mx-auto p-4 rounded-lg bg-arcade-bg border border-arcade-border space-y-4 text-left">
              <div className="text-xs font-mono font-bold text-arcade-subtle uppercase flex items-center justify-between">
                <span>SELECT YOUR SECRET VALUE (1 - 10):</span>
                <span className="text-arcade-pink font-bold text-sm">#{selectedCommitValue}</span>
              </div>

              <div className="grid grid-cols-5 gap-2">
                {Array.from({ length: 10 }, (_, i) => i + 1).map((val) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => setSelectedCommitValue(val)}
                    className={`h-11 rounded font-display text-base font-bold border transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-pink ${
                      selectedCommitValue === val
                        ? 'bg-arcade-pink text-black border-arcade-pink shadow-arcade-pink scale-105'
                        : 'bg-arcade-panel text-arcade-text border-arcade-border hover:border-arcade-pink/50'
                    }`}
                  >
                    {val}
                  </button>
                ))}
              </div>

              <p className="text-[11px] font-mono text-arcade-subtle">
                Your secret value is cryptographically hashed with local salt. The creator cannot view your card until showdown.
              </p>

              <ArcadeButton
                variant="pink"
                size="lg"
                className="w-full text-sm font-bold shadow-arcade-pink"
                isLoading={isSubmitting}
                onClick={async () => {
                  try {
                    await joinDuel(selectedCommitValue);
                    refresh();
                  } catch {
                    // Handled in hook
                  }
                }}
              >
                <Swords className="w-4 h-4 mr-2" />
                ACCEPT CHALLENGE & JOIN ({match.stake_amount} MON)
              </ArcadeButton>

              <div className="pt-2 border-t border-arcade-border flex items-center justify-between gap-3">
                <span className="text-[11px] font-mono text-arcade-subtle">PREFER TO TEST SOLO?</span>
                <ArcadeButton
                  variant="cyan"
                  size="sm"
                  isLoading={isSubmitting}
                  onClick={async () => {
                    try {
                      await spawnBot();
                      refresh();
                    } catch {
                      // Handled in hook
                    }
                  }}
                >
                  <Bot className="w-3.5 h-3.5 mr-1.5" />
                  PLAY WITH LOCAL BOT
                </ArcadeButton>
              </div>
            </div>
          </div>
        </Panel>
      )}

      {/* 2. WAITING FOR OPPONENT (CREATOR LOBBY VIEW) */}
      {match.status === 'WAITING' && isCreator && (
        <Panel header="WAITING FOR OPPONENT TO JOIN" accent="pink">
          <div className="py-6 text-center space-y-5">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-arcade-pink/10 border border-arcade-pink/40 text-arcade-pink animate-pulse motion-reduce:animate-none">
              <Swords className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h2 className="font-display text-base text-arcade-text tracking-wide uppercase">
                DUEL IS OPEN &bull; AWAITING OPPONENT
              </h2>
              <p className="text-xs font-mono text-arcade-muted max-w-sm mx-auto">
                Share this link with your opponent, or spawn an instant simulated bot to test right away.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-2 max-w-md mx-auto p-2 rounded bg-arcade-bg border border-arcade-border font-mono text-xs">
              <span className="text-arcade-subtle truncate flex-1 px-1">
                {window.location.href}
              </span>
              <ArcadeButton variant="secondary" size="sm" onClick={handleCopyLink}>
                {copiedLink ? (
                  <>
                    <Check className="w-3.5 h-3.5 mr-1 text-arcade-lime" />
                    COPIED LINK
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 mr-1" />
                    COPY LINK
                  </>
                )}
              </ArcadeButton>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <ArcadeButton
                variant="cyan"
                size="md"
                isLoading={isSubmitting}
                onClick={async () => {
                  try {
                    await spawnBot();
                    refresh();
                  } catch {
                    // Handled in hook
                  }
                }}
              >
                <Bot className="w-4 h-4 mr-1.5" />
                PLAY VS SIMULATED BOT
              </ArcadeButton>

              <ArcadeButton
                variant="secondary"
                size="md"
                isLoading={isSubmitting}
                onClick={async () => {
                  try {
                    await cancelMatch();
                    navigate('/bluff');
                  } catch {
                    // Handled in hook
                  }
                }}
              >
                <X className="w-4 h-4 mr-1.5 text-arcade-danger" />
                CANCEL DUEL
              </ArcadeButton>
            </div>
          </div>
        </Panel>
      )}

      {/* CORE DUEL ARENA: 1. PLAYER HIDDEN STATE vs 2. OPPONENT STATE */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. PLAYER'S HIDDEN NUMBER / STATE */}
        <Panel
          header="1. YOUR SECRET NUMBER (HIDDEN)"
          accent="pink"
          className="relative overflow-hidden"
        >
          <div className="py-6 flex flex-col items-center justify-center text-center space-y-4">
            {isSeatOpen && !isCreator ? (
              <div className="space-y-3">
                <div className="w-28 h-40 rounded-xl bg-arcade-bg border-2 border-dashed border-arcade-pink/50 flex flex-col items-center justify-center p-3 select-none text-arcade-subtle space-y-2 mx-auto">
                  <Swords className="w-8 h-8 text-arcade-pink animate-pulse motion-reduce:animate-none" />
                  <span className="text-[10px] font-mono uppercase text-arcade-pink font-bold">JOIN DUEL</span>
                </div>
                <p className="text-xs font-mono text-arcade-muted max-w-xs">
                  Accept the challenge in the panel above to choose your secret card.
                </p>
              </div>
            ) : match.status === 'ACTIVE' && myPlayer && !myPlayer.has_committed ? (
              <div className="w-full space-y-4">
                <p className="text-xs font-mono text-arcade-subtle">
                  CHOOSE YOUR SECRET VALUE (1 - 10)
                </p>
                <div className="grid grid-cols-5 gap-2 max-w-xs mx-auto">
                  {Array.from({ length: 10 }, (_, i) => i + 1).map((val) => (
                    <button
                      key={val}
                      onClick={() => setSelectedCommitValue(val)}
                      className={`h-11 rounded font-display text-lg font-bold border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-pink ${
                        selectedCommitValue === val
                          ? 'bg-arcade-pink text-black border-arcade-pink shadow-arcade-pink'
                          : 'bg-arcade-bg text-arcade-text border-arcade-border hover:border-arcade-pink/50'
                      }`}
                    >
                      {val}
                    </button>
                  ))}
                </div>
                <ArcadeButton
                  variant="pink"
                  size="md"
                  className="w-full max-w-xs"
                  isLoading={isSubmitting}
                  onClick={() => commitSecret(selectedCommitValue)}
                >
                  LOCK SECRET #{selectedCommitValue}
                </ArcadeButton>
              </div>
            ) : (
              <>
                <div className="relative group">
                  <div className="w-28 h-40 rounded-xl bg-arcade-bg border-2 border-arcade-pink/70 shadow-arcade-pink flex flex-col items-center justify-between p-3 select-none transition-transform hover:scale-[1.02] motion-reduce:hover:scale-100">
                    <div className="w-full flex justify-between items-center text-[10px] font-mono text-arcade-pink font-bold">
                      <span>VAL</span>
                      <EyeOff className="w-3.5 h-3.5 text-arcade-pink" />
                    </div>

                    <div className="flex flex-col items-center justify-center space-y-1 my-auto">
                      {myPlayer?.secret_value ?? myRevealedValue ? (
                        <div className="font-display text-5xl text-arcade-pink font-bold tracking-tight">
                          {myPlayer?.secret_value ?? myRevealedValue}
                        </div>
                      ) : (
                        <>
                          <Lock className="w-8 h-8 text-arcade-pink animate-pulse motion-reduce:animate-none" />
                          <span className="font-display text-xs text-arcade-pink font-bold tracking-wider">LOCKED</span>
                        </>
                      )}
                    </div>

                    <div className="text-[9px] font-mono text-arcade-subtle tracking-wider uppercase">
                      CONFIDENTIAL
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 max-w-xs">
                  <div className="inline-flex items-center gap-1.5 text-xs font-mono text-arcade-pink bg-arcade-pink/10 px-2.5 py-1 rounded border border-arcade-pink/30">
                    <EyeOff className="w-3.5 h-3.5" />
                    <span>LOCKED &bull; HIDDEN FROM OPPONENT</span>
                  </div>

                  {myPlayer?.commitment_hash && (
                    <div className="text-[10px] font-mono text-arcade-subtle flex items-center justify-center gap-1">
                      <span>HASH:</span>
                      <span className="text-arcade-text">{myPlayer.commitment_hash.slice(0, 10)}...</span>
                      <button
                        onClick={() => handleCopyHash(myPlayer.commitment_hash!)}
                        className="text-arcade-subtle hover:text-arcade-pink"
                        title="Copy Commitment Hash"
                      >
                        {copiedHash ? (
                          <Check className="w-3 h-3 text-arcade-lime" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  )}

                  {myAction && (
                    <div className="text-xs font-mono font-bold text-arcade-cyan pt-1">
                      YOUR ACTION: {myAction}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </Panel>

        {/* 2. OPPONENT STATE */}
        <Panel
          header={`2. OPPONENT (${opponentPlayer?.player_id ? opponentPlayer.player_id.slice(0, 10) : 'WAITING'})`}
          accent="cyan"
          className="relative overflow-hidden"
        >
          <div className="py-6 flex flex-col items-center justify-center text-center space-y-4">
            {!opponentPlayer ? (
              <div className="w-28 h-40 rounded-xl bg-arcade-bg/50 border-2 border-dashed border-arcade-border flex flex-col items-center justify-center p-3 select-none text-arcade-subtle space-y-2">
                <Swords className="w-6 h-6 animate-pulse motion-reduce:animate-none" />
                <span className="text-[10px] font-mono uppercase">EMPTY SEAT</span>
              </div>
            ) : match.status === 'RESOLVED' && theirRevealedValue !== null && theirRevealedValue !== undefined ? (
              <>
                <div className="w-28 h-40 rounded-xl bg-arcade-bg border-2 border-arcade-cyan/70 shadow-arcade-cyan flex flex-col items-center justify-between p-3 select-none">
                  <div className="w-full flex justify-between items-center text-[10px] font-mono text-arcade-cyan font-bold">
                    <span>VAL</span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-arcade-lime" />
                  </div>

                  <div className="font-display text-5xl text-arcade-cyan font-bold tracking-tight">
                    {theirRevealedValue}
                  </div>

                  <div className="text-[9px] font-mono text-arcade-lime tracking-wider uppercase font-bold">
                    REVEALED
                  </div>
                </div>

                <div className="space-y-1 max-w-xs">
                  <div className="inline-flex items-center gap-1.5 text-xs font-mono text-arcade-lime bg-arcade-lime/10 px-2.5 py-1 rounded border border-arcade-lime/30">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>HASH CRYPTOGRAPHICALLY VERIFIED</span>
                  </div>
                  {opponentPlayer?.action && (
                    <div className="text-xs font-mono font-bold text-arcade-cyan">
                      OPPONENT ACTION: {opponentPlayer.action}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <div className="w-28 h-40 rounded-xl bg-gradient-to-br from-arcade-panel to-arcade-bg border-2 border-arcade-border shadow-inner flex flex-col items-center justify-between p-3 select-none relative overflow-hidden group">
                  <div className="absolute inset-0 opacity-15 bg-[radial-gradient(rgba(255,62,165,0.3)_1px,transparent_1px)] [background-size:8px_8px]" />

                  <div className="w-full flex justify-between items-center text-[10px] font-mono text-arcade-subtle">
                    <Shield className="w-3.5 h-3.5 text-arcade-subtle" />
                    <span className="text-[9px]">MASKED</span>
                  </div>

                  <div className="font-display text-4xl text-arcade-subtle/70 font-bold z-10">
                    ?
                  </div>

                  <div className="text-[9px] font-mono text-arcade-subtle tracking-widest uppercase z-10">
                    ENCRYPTED
                  </div>
                </div>

                <div className="space-y-1.5 max-w-xs">
                  <div className="inline-flex items-center gap-1.5 text-xs font-mono text-arcade-subtle bg-arcade-panel px-2.5 py-1 rounded border border-arcade-border">
                    <Shield className="w-3.5 h-3.5 text-arcade-pink" />
                    <span>
                      {opponentPlayer?.has_committed
                        ? 'SECRET COMMITTED & HIDDEN'
                        : 'AWAITING SECRET COMMITMENT'}
                    </span>
                  </div>

                  {isOpponentTurn && (
                    <div className="text-xs font-mono text-arcade-cyan animate-pulse motion-reduce:animate-none">
                      OPPONENT IS DECIDING ACTION...
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </Panel>
      </div>

      {/* 3 & 4. COUNTDOWN AND PUSH / FOLD ACTIONS */}
      <Panel header="3 & 4. DECISION ENGINE & ACTIONS" accent="pink">
        <div className="py-4 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded bg-arcade-bg border border-arcade-border">
            <div className="flex items-center gap-2">
              <div
                className={`w-2.5 h-2.5 rounded-full ${
                  isPlayerTurn
                    ? 'bg-arcade-pink animate-ping motion-reduce:animate-none'
                    : isOpponentTurn
                    ? 'bg-arcade-cyan animate-pulse motion-reduce:animate-none'
                    : 'bg-arcade-subtle'
                }`}
              />
              <span className="text-xs font-mono font-bold tracking-wide text-arcade-text">
                {match.status === 'DECISION'
                  ? isPlayerTurn
                    ? 'YOUR MOVE: CHOOSE PUSH OR FOLD'
                    : isOpponentTurn
                    ? "OPPONENT'S TURN TO ACT"
                    : 'AWAITING ACTIONS'
                  : match.status === 'RESOLVED'
                  ? 'SHOWDOWN RESOLVED BY SERVER'
                  : match.status === 'ACTIVE'
                  ? 'COMMIT PHASE IN PROGRESS'
                  : 'WAITING FOR PLAYERS'}
              </span>
            </div>

            {match.status === 'DECISION' && (
              <LocalizedTurnTimer
                initialSeconds={match.seconds_remaining}
                isActive={true}
                isPlayerTurn={isPlayerTurn}
              />
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* PUSH Action Box */}
            <div className="p-4 rounded-lg bg-arcade-bg border border-arcade-border flex flex-col justify-between space-y-3">
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-arcade-pink">
                  <Flame className="w-4 h-4 text-arcade-pink" />
                  <span>ACTION: PUSH</span>
                </div>
                <p className="text-xs font-mono text-arcade-muted leading-relaxed">
                  Call the duel. If your secret value meets or exceeds the opponent&apos;s, you win the entire pot (
                  {match.pot_amount} MON).
                </p>
              </div>

              <ArcadeButton
                variant="pink"
                size="lg"
                className="w-full"
                isLoading={isSubmitting}
                disabled={!isPlayerTurn || match.status !== 'DECISION'}
                onClick={() => submitDecision('PUSH')}
              >
                <Flame className="w-4 h-4 mr-1.5" />
                PUSH (CHALLENGE)
              </ArcadeButton>
            </div>

            {/* FOLD Action Box */}
            <div className="p-4 rounded-lg bg-arcade-bg border border-arcade-border flex flex-col justify-between space-y-3">
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-arcade-subtle">
                  <Flag className="w-4 h-4 text-arcade-subtle" />
                  <span>ACTION: FOLD</span>
                </div>
                <p className="text-xs font-mono text-arcade-muted leading-relaxed">
                  Concede the duel. Opponent takes the pot without revealing. Prevents showdown loss penalty.
                </p>
              </div>

              <ArcadeButton
                variant="secondary"
                size="lg"
                className="w-full"
                isLoading={isSubmitting}
                disabled={!isPlayerTurn || match.status !== 'DECISION'}
                onClick={() => submitDecision('FOLD')}
              >
                <Flag className="w-4 h-4 mr-1.5" />
                FOLD (CONCEDE)
              </ArcadeButton>
            </div>
          </div>

          <div className="flex items-start gap-2 p-3 rounded bg-arcade-panel/50 border border-arcade-border text-[11px] font-mono text-arcade-subtle">
            <HelpCircle className="w-4 h-4 text-arcade-subtle shrink-0 mt-0.5" />
            <div>
              <span className="text-arcade-text font-bold uppercase">Authoritative Persistence: </span>
              Duel state is stored in memory and synchronized to PostgreSQL. Reconnecting or refreshing the page
              reconstructs your turn, remaining time, and hidden commitments without data loss.
            </div>
          </div>
        </div>
      </Panel>

      {/* 5. ROUND / MATCH RESOLUTION STATUS */}
      {match.status === 'RESOLVED' && (
        <Panel
          header="5. AUTHORITATIVE RESULT & SHOWDOWN"
          accent={match.winner_id === playerId ? 'lime' : match.winner_id ? 'pink' : 'cyan'}
        >
          <div className="py-6 text-center space-y-5">
            <div>
              <span
                className={`inline-block font-display text-2xl tracking-wider uppercase px-4 py-1.5 rounded border ${
                  match.winner_id === playerId
                    ? 'bg-arcade-lime/15 border-arcade-lime text-arcade-lime shadow-arcade-lime'
                    : match.winner_id
                    ? 'bg-arcade-danger/15 border-arcade-danger text-arcade-danger'
                    : 'bg-arcade-cyan/15 border-arcade-cyan text-arcade-cyan'
                }`}
              >
                {match.winner_id === playerId
                  ? 'VICTORY — YOU WON!'
                  : match.winner_id
                  ? 'DEFEAT — OPPONENT WON'
                  : 'DRAW — STAKES RETURNED'}
              </span>
              <p className="text-xs font-mono text-arcade-muted mt-2">
                REASON: {match.resolution_reason || 'SHOWDOWN COMPLETED'}
              </p>
            </div>

            <div className="max-w-xs mx-auto p-3 rounded bg-arcade-bg border border-arcade-border font-mono text-xs">
              <span className="text-arcade-subtle">POT SETTLEMENT: </span>
              <span className="text-arcade-lime font-bold">{match.pot_amount} MON</span>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2 w-full max-w-md mx-auto">
              <Link to={`/bluff/${match.id}/result`} className="w-full sm:w-auto">
                <ArcadeButton variant="pink" size="md" className="w-full sm:w-auto">
                  <span>VIEW FULL SHOWDOWN REPORT</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </ArcadeButton>
              </Link>
              <Link to="/bluff" className="w-full sm:w-auto">
                <ArcadeButton variant="secondary" size="md" className="w-full sm:w-auto">
                  NEW DUEL
                </ArcadeButton>
              </Link>
            </div>
          </div>
        </Panel>
      )}

      {/* Spectator Notice */}
      {isSpectator && (
        <div className="p-3 rounded bg-arcade-panel border border-arcade-border text-center text-xs font-mono text-arcade-subtle">
          YOU ARE SPECTATING DUEL #{match.id ? match.id.slice(0, 8) : matchId ? matchId.slice(0, 8) : ''}. ALL HIDDEN VALUES REMAIN MASKED UNTIL SHOWDOWN.
        </div>
      )}
    </PageContainer>
  );
};
