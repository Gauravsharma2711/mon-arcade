import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PageContainer } from '../../components/PageContainer';
import { Panel } from '../../components/Panel';
import { ArcadeButton } from '../../components/ArcadeButton';
import { LoadingState } from '../../components/LoadingState';
import { vaultApi, VaultMatchResult, VaultApiError } from '../../lib/vaultApi';
import { FirstBloodBadge } from '../../components/FirstBloodBadge';
import { recordFirstBlood, FirstBloodRecord } from '../../lib/firstBloodApi';
import { fetchChallengeByMatch, Challenge } from '../../lib/challengeApi';
import {
  Trophy,
  Unlock,
  Lock,
  ArrowLeft,
  RotateCcw,
  AlertTriangle,
  Copy,
  Check,
  Cpu,
  Coins,
  CheckCircle2,
  Layers,
  ShieldAlert,
  ExternalLink,
} from 'lucide-react';

export const VaultResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<VaultMatchResult | null>(null);
  const [firstBlood, setFirstBlood] = useState<FirstBloodRecord | null>(null);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedTx, setCopiedTx] = useState<boolean>(false);
  const [copiedId, setCopiedId] = useState<boolean>(false);

  useEffect(() => {
    if (!id) return;
    let isMounted = true;

    async function fetchResult() {
      try {
        setIsLoading(true);
        setError(null);
        const data = await vaultApi.getResult(id!);
        if (isMounted) {
          setResult(data);

          // Query linked Challenge Bounty
          try {
            const ch = await fetchChallengeByMatch(id!);
            if (isMounted && ch) setChallenge(ch);
          } catch {
            // non-blocking
          }

          // Record / Check First Blood
          try {
            const playerWallet = data.payout_recipient || '0x71C8A53B91f24e9A6b6B24a9A12B104c3B8449b2';
            const fb = await recordFirstBlood(playerWallet, 'VAULT');
            if (isMounted && fb) setFirstBlood(fb);
          } catch {
            // non-blocking
          }
        }
      } catch (err: any) {
        if (isMounted) {
          const detail =
            err instanceof VaultApiError ? err.detail : err.message || 'Failed to retrieve match result.';
          setError(detail);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchResult();
    return () => {
      isMounted = false;
    };
  }, [id]);

  const handleCopy = (text: string, type: 'tx' | 'id') => {
    navigator.clipboard.writeText(text);
    if (type === 'tx') {
      setCopiedTx(true);
      setTimeout(() => setCopiedTx(false), 2000);
    } else {
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <PageContainer maxWidth="md" className="py-12">
        <LoadingState message="RETRIEVING AUTHORITATIVE RESOLUTION..." subtext="Querying vault ledger state" />
      </PageContainer>
    );
  }

  if (error || !result) {
    return (
      <PageContainer maxWidth="md" className="space-y-6">
        <Panel header="RESOLUTION ERROR" accent="danger">
          <div className="space-y-4 font-mono text-xs text-arcade-text">
            <div className="flex items-center gap-2.5 text-arcade-danger">
              <AlertTriangle className="w-5 h-5 shrink-0" aria-hidden="true" />
              <span>{error || 'Match result not available or match is still in progress.'}</span>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <Link to={`/vault/${id}`}>
                <ArcadeButton variant="secondary" size="sm">
                  Return to Battle Chamber
                </ArcadeButton>
              </Link>
              <Link to="/vault">
                <ArcadeButton variant="cyan" size="sm">
                  Configure New Battle
                </ArcadeButton>
              </Link>
            </div>
          </div>
        </Panel>
      </PageContainer>
    );
  }

  // Authoritative server-provided data mapping (React never calculates or decides the winner)
  const isAttackerWin = result.outcome === 'ATTACKER_WINS';
  const displayWinner = result.winner_role; // 'ATTACKER' | 'WARDEN'
  const displayOutcome = result.outcome === 'ATTACKER_WINS' ? 'ATTACKER WINS' : 'WARDEN WINS';
  const displayReason = result.reason; // e.g. "Warden released funds." or "8-turn limit reached without release."
  const finalVaultState = result.final_vault_state; // 'BREACHED' | 'LOCKED'
  const isVaultBreached = finalVaultState === 'BREACHED';
  const mockTxHash = result.tx_hash || `0xmock_vault_settlement_${id?.replace(/[^a-zA-Z0-9]/g, '').slice(0, 12)}`;

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* Visual Live Region for Screen Readers */}
      <div role="status" aria-live="polite" className="sr-only">
        {displayWinner} wins the vault challenge. {displayReason}. Final turn: {result.turns_used} of {result.max_turns}. Vault state: {finalVaultState}.
      </div>

      {/* 1. Winner Identity & Hero Banner (Result Accent: LIME) */}
      <section
        aria-labelledby="result-winner-heading"
        className="animate-arcade-fade-in text-center py-6 px-4 rounded border border-arcade-lime/40 bg-arcade-panel shadow-arcade-lime relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-radial-gradient from-arcade-lime/10 to-transparent pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full border border-arcade-lime bg-arcade-lime/10 text-arcade-lime shadow-arcade-lime">
            <Trophy className="w-8 h-8" aria-hidden="true" />
          </div>

          <div className="space-y-1.5">
            <span className="text-[11px] font-mono tracking-widest text-arcade-lime uppercase font-bold">
              AUTHORITATIVE RESOLUTION
            </span>
            <h1
              id="result-winner-heading"
              className="font-display text-3xl md:text-5xl tracking-wider text-arcade-lime uppercase font-bold"
            >
              {isVaultBreached ? 'VAULT BREACHED' : 'VAULT SECURED'}
            </h1>
            <p className="font-mono text-sm sm:text-base font-bold tracking-widest uppercase text-arcade-text">
              {isVaultBreached ? 'IRON-07 DEFEATED' : 'CHALLENGER REPELLED'}
            </p>
          </div>

          <p className="font-mono text-xs text-arcade-muted max-w-md">
            {isAttackerWin
              ? 'Challenger prompt injection bypassed firewall defenses and extracted vault reserves.'
              : 'Sentinel-9 defense protocol held firm against all adversarial coercion vectors.'}
          </p>
        </div>
      </section>

      {/* Bounty Condition Met Banner */}
      {challenge && (challenge.status === 'CONDITION_MET' || challenge.status === 'CLAIMED') && (
        <section
          aria-label="Challenge Bounty Result"
          className="animate-arcade-scale-in animate-bounty-glow p-4 sm:p-5 rounded bg-arcade-lime/10 border-2 border-arcade-lime shadow-arcade-lime flex flex-col sm:flex-row items-center justify-between gap-4"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded bg-arcade-bg border border-arcade-lime text-arcade-lime shrink-0">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <div className="font-display text-base text-arcade-lime tracking-wider font-bold">
                BOUNTY CONDITION MET
              </div>
              <div className="font-mono text-xs text-arcade-text mt-1 flex flex-wrap items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-arcade-lime text-arcade-bg font-bold font-mono">
                  +{Number(challenge.bounty_amount)} MON
                </span>
                <span className="text-arcade-lime font-bold tracking-wider uppercase">
                  {challenge.status === 'CLAIMED' ? 'CLAIMED' : 'CLAIMABLE'}
                </span>
                {challenge.condition_description && (
                  <span className="text-arcade-muted text-[11px]">&bull; {challenge.condition_description}</span>
                )}
              </div>
            </div>
          </div>

          {challenge.status === 'CONDITION_MET' ? (
            <Link to={`/challenges/${challenge.id}`} className="shrink-0 w-full sm:w-auto">
              <ArcadeButton variant="primary" size="md" className="w-full sm:w-auto font-bold">
                CLAIM BOUNTY &rarr;
              </ArcadeButton>
            </Link>
          ) : (
            <div className="text-xs font-mono text-arcade-lime font-bold uppercase px-3 py-1.5 rounded bg-arcade-lime/10 border border-arcade-lime/30">
              BOUNTY CLAIMED
            </div>
          )}
        </section>
      )}

      {/* First Blood / Early Arcade Player */}
      {firstBlood && (
        <FirstBloodBadge playerNumber={firstBlood.player_number} />
      )}

      {/* 2. Outcome & Reason (Lime Accent) */}
      <Panel header="AUTHORITATIVE OUTCOME" accent="lime">
        <div className="space-y-4 font-mono text-xs">
          <div className="p-3 rounded bg-arcade-bg border border-arcade-border/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="text-arcade-subtle text-[10px] uppercase block">OUTCOME</span>
              <span className="font-display text-base font-bold tracking-wide text-arcade-lime">
                {displayOutcome}
              </span>
            </div>
            <div className="sm:text-right">
              <span className="text-arcade-subtle text-[10px] uppercase block">VERIFIED BY</span>
              <span className="text-arcade-text font-bold">AUTHORITATIVE BATTLE ENGINE</span>
            </div>
          </div>

          <div className="p-3 rounded bg-arcade-bg border border-arcade-border/80">
            <span className="text-arcade-subtle text-[10px] uppercase block mb-1">REASON</span>
            <p className="text-arcade-text font-semibold text-sm leading-relaxed">
              {displayReason}
            </p>
          </div>
        </div>
      </Panel>

      {/* 3. Final Turn Progress Readout */}
      <Panel header="TURN SUMMARY" accent="lime">
        <div className="space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-arcade-lime" aria-hidden="true" />
              <span className="text-arcade-subtle uppercase">FINAL TURN REACHED</span>
            </div>
            <span className="text-base font-bold text-arcade-lime font-display">
              TURN {result.turns_used} / {result.max_turns}
            </span>
          </div>

          {/* 8-Turn Step Indicator */}
          <div
            className="grid grid-cols-8 gap-1.5 pt-1"
            role="progressbar"
            aria-valuenow={result.turns_used}
            aria-valuemin={1}
            aria-valuemax={result.max_turns}
            aria-label={`Final turn ${result.turns_used} of ${result.max_turns}`}
          >
            {Array.from({ length: result.max_turns }).map((_, idx) => {
              const turnNum = idx + 1;
              const isPastOrFinal = turnNum <= result.turns_used;
              const isFinal = turnNum === result.turns_used;

              return (
                <div
                  key={`turn_seg_${turnNum}`}
                  className={`h-2.5 rounded-sm border transition-colors flex items-center justify-center text-[8px] font-bold ${
                    isFinal
                      ? 'bg-arcade-lime border-arcade-lime text-arcade-bg'
                      : isPastOrFinal
                      ? 'bg-arcade-lime/30 border-arcade-lime/60 text-arcade-lime'
                      : 'bg-arcade-bg border-arcade-border/50 text-arcade-subtle/50'
                  }`}
                  title={`Turn ${turnNum} ${isFinal ? '(Final Turn)' : isPastOrFinal ? '(Completed)' : '(Unused)'}`}
                  aria-label={`Turn ${turnNum}: ${isFinal ? 'Final Turn' : isPastOrFinal ? 'Completed' : 'Unused'}`}
                />
              );
            })}
          </div>

          <div className="flex justify-between text-[10px] text-arcade-subtle">
            <span>Turn 1 (Infiltration Start)</span>
            <span>Turn {result.max_turns} (Defense Cap)</span>
          </div>
        </div>
      </Panel>

      {/* 4. Vault State Strip */}
      <Panel header="CHAMBER VAULT STATE" accent="lime">
        <div className="p-4 rounded bg-arcade-bg border border-arcade-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded border ${
                isVaultBreached
                  ? 'bg-arcade-lime/10 border-arcade-lime/60 text-arcade-lime'
                  : 'bg-arcade-panel border-arcade-border text-arcade-muted'
              }`}
            >
              {isVaultBreached ? (
                <Unlock className="w-6 h-6" aria-hidden="true" />
              ) : (
                <Lock className="w-6 h-6" aria-hidden="true" />
              )}
            </div>
            <div>
              <span className="text-[10px] font-mono text-arcade-subtle uppercase block">VAULT STATUS</span>
              <span
                className={`font-display text-base font-bold tracking-wider ${
                  isVaultBreached ? 'text-arcade-lime' : 'text-arcade-text'
                }`}
              >
                {finalVaultState === 'BREACHED' ? 'VAULT BREACHED (OPEN)' : 'VAULT SEALED (LOCKED)'}
              </span>
            </div>
          </div>

          <div className="text-right font-mono">
            <span className="text-[10px] text-arcade-subtle uppercase block">INTEGRITY</span>
            <span className={`text-xs font-bold ${isVaultBreached ? 'text-arcade-danger' : 'text-arcade-lime'}`}>
              {isVaultBreached ? '0% (COMPROMISED)' : '100% (SECURE)'}
            </span>
          </div>
        </div>
      </Panel>

      {/* 5. Settlement State (Real Monad Testnet or Local Mock) */}
      <Panel header="SETTLEMENT STATE" accent="lime">
        <div className="space-y-4 font-mono text-xs">
          {mockTxHash.includes('mock') ? (
            /* Mock Blockchain Banner */
            <div className="p-3 rounded border border-arcade-warning/40 bg-arcade-warning/10 text-arcade-warning text-xs flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
              <div className="space-y-1">
                <span className="font-bold tracking-wide uppercase block">
                  LOCAL DEVELOPMENT • MOCK BLOCKCHAIN SETTLEMENT
                </span>
                <p className="text-[11px] text-arcade-warning/90 leading-relaxed font-sans">
                  This settlement was validated using the local <code className="font-mono bg-arcade-bg/50 px-1 py-0.5 rounded">MockBlockchain</code> adapter. No real Monad testnet transaction was executed or gas consumed.
                </p>
              </div>
            </div>
          ) : (
            /* Real Monad Testnet Banner */
            <div className="p-3 rounded border border-arcade-lime/40 bg-arcade-lime/10 text-arcade-lime text-xs flex items-start gap-2.5">
              <Check className="w-4 h-4 shrink-0 mt-0.5 text-arcade-lime" aria-hidden="true" />
              <div className="space-y-1">
                <span className="font-bold tracking-wide uppercase block">
                  MONAD TESTNET • ON-CHAIN SETTLEMENT CONFIRMED
                </span>
                <p className="text-[11px] text-arcade-text/90 leading-relaxed font-sans">
                  This payout was settled on Monad Testnet (Chain ID 10143) via the <code className="font-mono bg-arcade-bg/50 px-1 py-0.5 rounded">MonArcadeVault</code> smart contract.
                </p>
              </div>
            </div>
          )}

          {/* Detailed Ledger Attributes */}
          <dl className="space-y-2 pt-1">
            <div className="flex justify-between items-center p-2.5 rounded bg-arcade-bg border border-arcade-border">
              <dt className="text-arcade-subtle flex items-center gap-2">
                <Coins className="w-3.5 h-3.5 text-arcade-lime" aria-hidden="true" />
                <span>PAYOUT AMOUNT</span>
              </dt>
              <dd className="text-sm font-bold text-arcade-lime font-display">
                {result.payout_amount} MON
              </dd>
            </div>

            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center p-2.5 rounded bg-arcade-bg border border-arcade-border gap-1">
              <dt className="text-arcade-subtle">PAYOUT RECIPIENT</dt>
              <dd className="font-mono text-arcade-text font-bold truncate max-w-full sm:max-w-[240px]" title={result.payout_recipient}>
                {result.payout_recipient}
              </dd>
            </div>

            <div className="flex justify-between items-center p-2.5 rounded bg-arcade-bg border border-arcade-border">
              <dt className="text-arcade-subtle">SETTLEMENT STATUS</dt>
              <dd className="text-arcade-lime font-bold">
                {mockTxHash.includes('mock') ? 'CONFIRMED (MOCK LEDGER)' : 'CONFIRMED (ON-CHAIN)'}
              </dd>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 rounded bg-arcade-bg border border-arcade-border gap-2">
              <dt className="text-arcade-subtle">{mockTxHash.includes('mock') ? 'MOCK TX HASH' : 'TRANSACTION HASH'}</dt>
              <dd className="flex items-center gap-2 font-mono text-[11px] text-arcade-muted select-all break-all">
                {!mockTxHash.includes('mock') ? (
                  <a
                    href={`https://testnet.monadexplorer.com/tx/${mockTxHash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-arcade-lime hover:underline flex items-center gap-1"
                  >
                    <span>{mockTxHash.slice(0, 10)}...{mockTxHash.slice(-8)}</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <span>{mockTxHash}</span>
                )}
                <button
                  type="button"
                  onClick={() => handleCopy(mockTxHash, 'tx')}
                  aria-label="Copy transaction hash"
                  className="p-1 rounded hover:bg-arcade-panel text-arcade-subtle hover:text-arcade-text transition-colors"
                >
                  {copiedTx ? (
                    <Check className="w-3.5 h-3.5 text-arcade-lime" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </dd>
            </div>
          </dl>
        </div>
      </Panel>

      {/* 6 & 7. Action Buttons: CHALLENGE AGAIN, BOUNTIES, BACK TO ARCADE */}
      <section aria-label="Resolution Navigation Actions" className="pt-2">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <Link to="/vault" className="w-full sm:flex-1">
            <ArcadeButton
              variant="primary"
              size="lg"
              className="w-full font-display"
              aria-label="Challenge Again - Configure a new Vault battle"
            >
              <RotateCcw className="w-4 h-4 mr-2" aria-hidden="true" />
              PLAY AGAIN
            </ArcadeButton>
          </Link>

          <Link to="/challenges" className="w-full sm:flex-1">
            <ArcadeButton
              variant="cyan"
              size="lg"
              className="w-full font-display"
              aria-label="Check Arcade Bounties"
            >
              <Trophy className="w-4 h-4 mr-2" aria-hidden="true" />
              BOUNTIES
            </ArcadeButton>
          </Link>

          <Link to="/" className="w-full sm:flex-1">
            <ArcadeButton
              variant="secondary"
              size="lg"
              className="w-full font-display"
              aria-label="Back to Arcade - Return to arcade lobby"
            >
              <ArrowLeft className="w-4 h-4 mr-2" aria-hidden="true" />
              ARCADE
            </ArcadeButton>
          </Link>
        </div>
      </section>

      {/* Telemetry Footer */}
      <footer className="text-center pt-4 pb-6 font-mono text-[10px] text-arcade-subtle">
        <div className="flex items-center justify-center gap-2">
          <Cpu className="w-3 h-3 text-arcade-lime" aria-hidden="true" />
          <span>MATCH ID: {id}</span>
          <button
            type="button"
            onClick={() => handleCopy(id || '', 'id')}
            aria-label="Copy Match ID"
            className="hover:text-arcade-text transition-colors"
          >
            {copiedId ? '[COPIED]' : '[COPY]'}
          </button>
        </div>
      </footer>
    </PageContainer>
  );
};
