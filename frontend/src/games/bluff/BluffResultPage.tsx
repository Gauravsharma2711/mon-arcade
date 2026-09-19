import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { PageContainer } from '../../components/PageContainer';
import { Panel } from '../../components/Panel';
import { ArcadeButton } from '../../components/ArcadeButton';
import { LoadingState } from '../../components/LoadingState';
import { bluffApi, BluffMatchResult } from '../../lib/bluffApi';
import { getOrCreatePlayerId } from '../../hooks/useBluffLobby';
import { FirstBloodBadge } from '../../components/FirstBloodBadge';
import { recordFirstBlood, FirstBloodRecord } from '../../lib/firstBloodApi';
import {
  Trophy,
  ArrowLeft,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  ShieldAlert,
  Swords,
  Coins,
} from 'lucide-react';

/**
 * Format authoritative backend resolution reason into clean arcade text.
 */
function formatResolutionReason(reason: string): string {
  switch (reason) {
    case 'SHOWDOWN_HIGHER_CARD':
      return 'SHOWDOWN: HIGHER SECRET VALUE PREVAILED';
    case 'SHOWDOWN_TIE':
      return 'SHOWDOWN: IDENTICAL VALUES RESULTED IN A DRAW';
    case 'CREATOR_FOLDED':
      return 'CREATOR SURRENDERED (FOLD)';
    case 'OPPONENT_FOLDED':
      return 'OPPONENT SURRENDERED (FOLD)';
    case 'CREATOR_TIMEOUT':
      return 'CREATOR TURN TIMEOUT FORFEIT';
    case 'OPPONENT_TIMEOUT':
      return 'OPPONENT TURN TIMEOUT FORFEIT';
    default:
      return reason.replace(/_/g, ' ');
  }
}

export const BluffResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const matchId = id || '';
  const navigate = useNavigate();
  const playerId = getOrCreatePlayerId();

  const [result, setResult] = useState<BluffMatchResult | null>(null);
  const [firstBlood, setFirstBlood] = useState<FirstBloodRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRematching, setIsRematching] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<boolean>(false);
  const [copiedTx, setCopiedTx] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    async function loadResult() {
      if (!matchId) return;
      try {
        setIsLoading(true);
        setError(null);
        const data = await bluffApi.getResult(matchId, playerId);
        if (mounted) {
          setResult(data);
          try {
            const fb = await recordFirstBlood(playerId, 'BLUFF');
            if (mounted && fb) setFirstBlood(fb);
          } catch {
            // non-blocking
          }
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.message || 'Showdown result not available or match is still in progress');
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    }
    loadResult();
    return () => {
      mounted = false;
    };
  }, [matchId, playerId]);

  const handleCopyId = () => {
    if (!matchId) return;
    navigator.clipboard.writeText(matchId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleCopyTx = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedTx(true);
    setTimeout(() => setCopiedTx(false), 2000);
  };

  // Instant rematch action
  const handleRematch = async () => {
    setIsRematching(true);
    try {
      const defaultStake = result ? Number(result.pot_amount) / 2 || 5.0 : 5.0;
      const newMatch = await bluffApi.createMatch({
        creator_id: playerId,
        stake_amount: defaultStake,
        secret_value: Math.floor(Math.random() * 10) + 1,
      });
      navigate(`/bluff/${newMatch.id}`);
    } catch {
      navigate('/bluff');
    } finally {
      setIsRematching(false);
    }
  };

  // 1. Loading State
  if (isLoading) {
    return (
      <PageContainer maxWidth="md" className="py-12">
        <LoadingState message="FETCHING AUTHORITATIVE SHOWDOWN VERIFICATION..." />
      </PageContainer>
    );
  }

  // 2. Error / In-Progress State
  if (error && !result) {
    return (
      <PageContainer maxWidth="md" className="py-10 space-y-6">
        <Panel header="SHOWDOWN REPORT UNAVAILABLE" accent="danger">
          <div className="py-6 text-center space-y-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-arcade-warning/10 border border-arcade-warning/40 text-arcade-warning">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-display text-base text-arcade-text tracking-wide uppercase">
                DUEL STILL IN PROGRESS OR RESULT NOT READY
              </h2>
              <p className="text-xs font-mono text-arcade-subtle mt-1 max-w-sm mx-auto">{error}</p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-2">
              <Link to={`/bluff/${matchId}`}>
                <ArcadeButton variant="secondary" size="sm">
                  <ArrowLeft className="w-3.5 h-3.5 mr-1" />
                  RETURN TO DUEL ARENA
                </ArcadeButton>
              </Link>
              <Link to="/bluff">
                <ArcadeButton variant="secondary" size="sm">
                  BLUFF LOBBY
                </ArcadeButton>
              </Link>
            </div>
          </div>
        </Panel>
      </PageContainer>
    );
  }

  if (!result) return null;

  // Derive viewer role and outcomes authoritatively from backend result
  const isWinner = result.winner_id === playerId;
  const isLoser = result.loser_id === playerId;
  const isDraw = result.is_tie || result.winner_id === null;

  const isCreator = result.creator_revealed.player_id === playerId;
  const myRevealed = isCreator ? result.creator_revealed : result.opponent_revealed;
  const oppRevealed = isCreator ? result.opponent_revealed : result.creator_revealed;

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* 1. OUTCOME (Lime primary accent) */}
      <div className="animate-arcade-fade-in text-center py-6 space-y-4 border-b border-arcade-border">
        <div
          className={`inline-flex items-center justify-center w-20 h-20 rounded-full border-2 transition-transform select-none ${
            isWinner
              ? 'bg-arcade-lime/15 border-arcade-lime text-arcade-lime shadow-arcade-lime'
              : isDraw
              ? 'bg-arcade-cyan/15 border-arcade-cyan text-arcade-cyan shadow-arcade-cyan'
              : 'bg-arcade-danger/15 border-arcade-danger text-arcade-danger'
          }`}
        >
          {isWinner ? (
            <Trophy className="w-10 h-10" />
          ) : isDraw ? (
            <Swords className="w-10 h-10" />
          ) : (
            <ShieldAlert className="w-10 h-10" />
          )}
        </div>

        <div className="space-y-1">
          <h1
            className={`font-display text-3xl tracking-wider uppercase ${
              isWinner
                ? 'text-arcade-lime'
                : isDraw
                ? 'text-arcade-cyan'
                : 'text-arcade-danger'
            }`}
          >
            {isWinner
              ? 'VICTORY — DUEL WON'
              : isDraw
              ? 'DRAW — POT RETURNED'
              : isLoser
              ? 'DEFEAT — DUEL LOST'
              : `CONCLUDED: WINNER ${result.winner_id ? `${result.winner_id.slice(0, 8)}...` : 'NONE'}`}
          </h1>
          <p className="font-mono text-xs text-arcade-muted">
            {formatResolutionReason(result.resolution_reason)}
          </p>
        </div>

        {/* Explicit Winner and Loser Badges */}
        <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-arcade-lime/10 border border-arcade-lime/40 text-xs font-mono">
            <Trophy className="w-3.5 h-3.5 text-arcade-lime" />
            <span className="text-arcade-subtle">WINNER:</span>
            <span className="text-arcade-lime font-bold">
              {result.winner_id
                ? result.winner_id === playerId
                  ? `${result.winner_id.slice(0, 10)} (YOU)`
                  : result.winner_id.slice(0, 10)
                : 'NONE (TIED)'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-arcade-panel border border-arcade-border text-xs font-mono">
            <span className="text-arcade-subtle">LOSER:</span>
            <span className="text-arcade-muted font-bold">
              {result.loser_id
                ? result.loser_id === playerId
                  ? `${result.loser_id.slice(0, 10)} (YOU)`
                  : result.loser_id.slice(0, 10)
                : 'NONE (TIED)'}
            </span>
          </div>
        </div>
      </div>

      {/* Early Arcade Player: First Blood Badge */}
      {firstBlood && (
        <FirstBloodBadge playerNumber={firstBlood.player_number} />
      )}

      {/* 2. GAME RESULT (Authoritative Match Information) */}
      <Panel header="2. AUTHORITATIVE GAME RESULT" accent="lime">
        <div className="py-2 space-y-3 font-mono text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Match Identifier */}
            <div className="p-3 rounded bg-arcade-bg border border-arcade-border flex items-center justify-between">
              <div>
                <div className="text-[10px] text-arcade-subtle uppercase">MATCH ID</div>
                <div className="text-arcade-text font-bold mt-0.5">#{result.match_id ? result.match_id.slice(0, 8) : ''}</div>
              </div>
              <button
                onClick={handleCopyId}
                className="p-1 rounded text-arcade-subtle hover:text-arcade-lime"
                title="Copy Match ID"
                aria-label="Copy Match ID"
              >
                {copiedId ? <Check className="w-3.5 h-3.5 text-arcade-lime" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* Total Pot */}
            <div className="p-3 rounded bg-arcade-bg border border-arcade-border">
              <div className="text-[10px] text-arcade-subtle uppercase flex items-center gap-1">
                <Coins className="w-3 h-3 text-arcade-lime" />
                <span>TOTAL POT</span>
              </div>
              <div className="text-arcade-lime font-bold text-sm mt-0.5">{result.pot_amount} MON</div>
            </div>

            {/* Final Action / Decision */}
            <div className="p-3 rounded bg-arcade-bg border border-arcade-border">
              <div className="text-[10px] text-arcade-subtle uppercase">FINAL DECISION</div>
              <div className="text-arcade-cyan font-bold mt-0.5">
                {myRevealed?.action === 'PUSH' || oppRevealed?.action === 'PUSH'
                  ? 'PUSH (CALL CHALLENGE)'
                  : myRevealed?.action === 'FOLD' || oppRevealed?.action === 'FOLD'
                  ? 'FOLD (CONCESSION)'
                  : 'TIMED OUT'}
              </div>
            </div>
          </div>

          <div className="p-2.5 rounded bg-arcade-panel/50 border border-arcade-border text-[11px] text-arcade-subtle flex items-center justify-between">
            <span>SHOWDOWN STATUS: <strong className="text-arcade-text uppercase">{result.status}</strong></span>
            <span>RESOLVED AT: {new Date(result.resolved_at).toLocaleTimeString()}</span>
          </div>
        </div>
      </Panel>

      {/* 3. REVEALED VALUES (When Authorized by Server) */}
      <Panel header="3. REVEALED VALUES & COMMITMENT PROOF" accent="lime">
        <div className="py-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-center">
            {/* Player's Revealed Card */}
            <div className="p-4 rounded-lg bg-arcade-bg border-2 border-arcade-pink/50 shadow-[0_0_15px_rgba(255,62,165,0.15)] flex flex-col items-center justify-between space-y-3">
              <div className="w-full flex justify-between items-center text-[10px] font-mono">
                <span className="text-arcade-pink font-bold">
                  {myRevealed?.player_id ? `${myRevealed.player_id.slice(0, 10)} (YOU)` : 'YOU'}
                </span>
                <span className="text-arcade-subtle uppercase">
                  {myRevealed?.action ? `ACTION: ${myRevealed.action}` : 'NO ACTION'}
                </span>
              </div>

              <div className="font-display text-5xl text-arcade-pink font-bold tracking-tight py-2">
                {myRevealed?.secret_value ?? '—'}
              </div>

              <div className="w-full space-y-1.5 pt-2 border-t border-arcade-border text-[10px] font-mono">
                {myRevealed?.commitment_verified ? (
                  <div className="inline-flex items-center gap-1 text-arcade-lime font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>HASH CRYPTOGRAPHICALLY VERIFIED</span>
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-1 text-arcade-danger">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>VERIFICATION FAILED</span>
                  </div>
                )}
                <div className="text-arcade-subtle truncate max-w-full">
                  HASH: <span className="text-arcade-text">{myRevealed?.commitment_hash ? `${myRevealed.commitment_hash.slice(0, 14)}...` : '—'}</span>
                </div>
                <div className="text-arcade-subtle truncate max-w-full">
                  SALT: <span className="text-arcade-text">{myRevealed?.salt ? `${myRevealed.salt.slice(0, 14)}...` : '—'}</span>
                </div>
              </div>
            </div>

            {/* Opponent's Revealed Card */}
            <div className="p-4 rounded-lg bg-arcade-bg border-2 border-arcade-cyan/50 shadow-[0_0_15px_rgba(0,240,255,0.15)] flex flex-col items-center justify-between space-y-3">
              <div className="w-full flex justify-between items-center text-[10px] font-mono">
                <span className="text-arcade-cyan font-bold">
                  {oppRevealed?.player_id ? `${oppRevealed.player_id.slice(0, 10)} (OPPONENT)` : 'OPPONENT'}
                </span>
                <span className="text-arcade-subtle uppercase">
                  {oppRevealed?.action ? `ACTION: ${oppRevealed.action}` : 'NO ACTION'}
                </span>
              </div>

              <div className="font-display text-5xl text-arcade-cyan font-bold tracking-tight py-2">
                {oppRevealed?.secret_value ?? '—'}
              </div>

              <div className="w-full space-y-1.5 pt-2 border-t border-arcade-border text-[10px] font-mono">
                {oppRevealed?.commitment_verified ? (
                  <div className="inline-flex items-center gap-1 text-arcade-lime font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>HASH CRYPTOGRAPHICALLY VERIFIED</span>
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-1 text-arcade-danger">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>VERIFICATION FAILED</span>
                  </div>
                )}
                <div className="text-arcade-subtle truncate max-w-full">
                  HASH: <span className="text-arcade-text">{oppRevealed?.commitment_hash ? `${oppRevealed.commitment_hash.slice(0, 14)}...` : '—'}</span>
                </div>
                <div className="text-arcade-subtle truncate max-w-full">
                  SALT: <span className="text-arcade-text">{oppRevealed?.salt ? `${oppRevealed.salt.slice(0, 14)}...` : '—'}</span>
                </div>
              </div>
            </div>
          </div>

          <p className="text-[11px] font-mono text-arcade-subtle text-center">
            Revealed values and cryptographic salts verify SHA-256 commitments made at round start.
          </p>
        </div>
      </Panel>

      {/* 4. MONAD / SETTLEMENT STATUS PLACEHOLDER (Explicit Mock Representation) */}
      <Panel header="4. MONAD SETTLEMENT (LOCAL ENVIRONMENT)" accent="lime">
        <div className="py-3 space-y-3 font-mono text-xs">
          {/* Local Simulated Settlement Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded bg-arcade-bg border border-arcade-border">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-arcade-subtle uppercase">SETTLEMENT ENGINE:</span>
                <span className="text-arcade-lime font-bold">MOCK BLOCKCHAIN (LOCAL SIMULATION)</span>
              </div>
              <p className="text-[11px] text-arcade-muted leading-relaxed max-w-md">
                Settlement executed locally. No real Monad blockchain transaction occurred. Smart contract settlement runs via local simulation adapter.
              </p>
            </div>
            <div className="text-left sm:text-right shrink-0">
              <div className="text-[10px] text-arcade-subtle uppercase">SETTLED POT</div>
              <div className="text-arcade-lime font-bold text-base">{result.pot_amount} MON</div>
            </div>
          </div>

          {/* Simulated Transaction Hash */}
          {result.payout_tx_hash && (
            <div className="p-3 rounded bg-arcade-bg/60 border border-arcade-border text-[11px] flex flex-col sm:flex-row sm:items-center justify-between gap-2 min-w-0">
              <div className="flex items-center gap-2 text-arcade-subtle min-w-0 flex-1">
                <span className="shrink-0">SIMULATED TX HASH:</span>
                <span className="text-arcade-muted font-mono truncate">{result.payout_tx_hash}</span>
                <button
                  onClick={() => handleCopyTx(result.payout_tx_hash!)}
                  className="text-arcade-subtle hover:text-arcade-lime shrink-0"
                  title="Copy Simulated Hash"
                  aria-label="Copy Simulated Hash"
                >
                  {copiedTx ? <Check className="w-3.5 h-3.5 text-arcade-lime" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <span className="text-[9px] font-bold text-arcade-warning px-2 py-0.5 rounded bg-arcade-warning/10 border border-arcade-warning/30 self-start sm:self-auto shrink-0">
                LOCAL SIMULATION ONLY
              </span>
            </div>
          )}

          <div className="text-[11px] text-arcade-subtle flex items-start gap-1.5 pt-1">
            <AlertCircle className="w-3.5 h-3.5 text-arcade-subtle shrink-0 mt-0.5" />
            <span>
              Authoritative resolution state: <strong className="text-arcade-text uppercase">{result.settlement_status}</strong>. React consumes server outcome strictly without calculating payouts.
            </span>
          </div>
        </div>
      </Panel>

      {/* 5 & 6. ACTION BUTTONS: REMATCH, BOUNTIES & BACK TO ARCADE */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
        {/* 5. REMATCH */}
        <ArcadeButton
          variant="primary"
          size="lg"
          className="w-full sm:flex-1 font-display"
          isLoading={isRematching}
          onClick={handleRematch}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          REMATCH
        </ArcadeButton>

        {/* BOUNTIES */}
        <Link to="/challenges" className="w-full sm:flex-1">
          <ArcadeButton variant="cyan" size="lg" className="w-full font-display">
            <Trophy className="w-4 h-4 mr-2" />
            BOUNTIES
          </ArcadeButton>
        </Link>

        {/* 6. BACK TO ARCADE */}
        <Link to="/" className="w-full sm:flex-1">
          <ArcadeButton variant="secondary" size="lg" className="w-full font-display">
            <ArrowLeft className="w-4 h-4 mr-2" />
            ARCADE
          </ArcadeButton>
        </Link>
      </div>
    </PageContainer>
  );
};
