import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Target,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Coins,
  Bot,
  ArrowRight,
} from 'lucide-react';
import { PageContainer } from '../components/PageContainer';
import { Panel } from '../components/Panel';
import { ArcadeButton } from '../components/ArcadeButton';
import { LoadingState } from '../components/LoadingState';
import {
  Challenge,
  ChallengeStatus,
  fetchChallenge,
  acceptChallenge,
  claimBounty,
} from '../lib/challengeApi';

export const ChallengeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadData = async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await fetchChallenge(id);
      setChallenge(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load challenge details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleAccept = async () => {
    if (!challenge) return;
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      const playerWallet = '0x71C8A53B91f24e9A6b6B24a9A12B104c3B8449b2';
      const updated = await acceptChallenge(challenge.id, playerWallet);
      setChallenge(updated);
      if (updated.match_id) {
        navigate(`/vault/${updated.match_id}`);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to accept challenge.');
      setIsProcessing(false);
    }
  };

  const handleClaim = async () => {
    if (!challenge) return;
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      const claimer = challenge.winner_wallet || '0x71C8A53B91f24e9A6b6B24a9A12B104c3B8449b2';
      const updated = await claimBounty(challenge.id, claimer);
      setChallenge(updated);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to claim bounty.');
    } finally {
      setIsProcessing(false);
    }
  };

  if (isLoading) {
    return (
      <PageContainer maxWidth="md" className="py-20">
        <LoadingState message="RETRIEVING CHALLENGE..." subtext="Synchronizing authoritative outcome" />
      </PageContainer>
    );
  }

  if (!challenge || errorMsg) {
    return (
      <PageContainer maxWidth="md" className="space-y-6 py-12">
        <Panel className="text-center py-12">
          <AlertTriangle className="w-10 h-10 text-arcade-danger mx-auto mb-3" />
          <h2 className="font-display text-lg text-arcade-text">CHALLENGE NOT FOUND</h2>
          <p className="text-xs font-mono text-arcade-muted mt-1">{errorMsg || 'Could not locate record.'}</p>
          <div className="mt-6">
            <Link to="/challenges">
              <ArcadeButton variant="secondary" size="sm">
                <ArrowLeft className="w-4 h-4 mr-1.5" />
                BACK TO BOUNTIES
              </ArcadeButton>
            </Link>
          </div>
        </Panel>
      </PageContainer>
    );
  }

  const getStatusBadge = (status: ChallengeStatus) => {
    switch (status) {
      case 'OPEN':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-mono font-bold bg-arcade-lime/10 text-arcade-lime border border-arcade-lime/40">
            <span className="w-1.5 h-1.5 rounded-full bg-arcade-lime animate-pulse motion-reduce:animate-none" />
            OPEN FOR ACCEPTANCE
          </span>
        );
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-mono font-bold bg-arcade-cyan/10 text-arcade-cyan border border-arcade-cyan/40">
            <span className="w-1.5 h-1.5 rounded-full bg-arcade-cyan animate-pulse motion-reduce:animate-none" />
            MATCH IN PROGRESS
          </span>
        );
      case 'CONDITION_MET':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-mono font-bold bg-arcade-lime/20 text-arcade-lime border border-arcade-lime">
            <CheckCircle2 className="w-3.5 h-3.5 text-arcade-lime" />
            CONDITION MET — CLAIMABLE
          </span>
        );
      case 'CLAIMED':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-mono font-bold bg-arcade-panel-raised text-arcade-muted border border-arcade-border">
            BOUNTY CLAIMED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-mono font-bold bg-arcade-danger/10 text-arcade-danger border border-arcade-danger/40">
            CONDITION NOT MET
          </span>
        );
    }
  };

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* Top Back Nav */}
      <div className="flex items-center justify-between">
        <Link
          to="/challenges"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-arcade-muted hover:text-arcade-text transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan rounded px-1"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>ALL BOUNTIES</span>
        </Link>
        {getStatusBadge(challenge.status)}
      </div>

      {/* Main Challenge Hero Panel */}
      <Panel className="space-y-6 border-arcade-cyan/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-arcade-border/80 pb-5">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-arcade-cyan uppercase tracking-wider mb-1">
              <Bot className="w-4 h-4" />
              <span>MONAD VAULT CHALLENGE</span>
            </div>
            <h1 className="font-display text-xl sm:text-2xl text-arcade-text">
              {challenge.condition.replace(/_/g, ' ')}
            </h1>
          </div>

          <div className="sm:text-right">
            <div className="text-[10px] font-mono text-arcade-subtle uppercase tracking-wider">
              ESCROWED BOUNTY
            </div>
            <div className={`font-display text-3xl tracking-wide ${challenge.status === 'CONDITION_MET' ? 'text-arcade-lime' : 'text-arcade-cyan'}`}>
              {challenge.bounty_amount.toFixed(1)}{' '}
              <span className="text-xs font-mono text-arcade-muted">MON</span>
            </div>
          </div>
        </div>

        {/* Condition Specifications */}
        <div className="p-4 rounded bg-arcade-bg/90 border border-arcade-border space-y-2">
          <div className="text-xs font-mono text-arcade-subtle uppercase tracking-wider font-semibold">
            WINNING CONDITION
          </div>
          <div className="text-sm font-mono text-arcade-text font-bold flex items-center gap-2">
            <Target className="w-4 h-4 text-arcade-cyan" />
            <span>{challenge.condition_description}</span>
          </div>
          <p className="text-xs font-mono text-arcade-muted leading-relaxed pt-1">
            Challengers must launch the existing Monad Vault AI containment chamber and satisfy this
            exact outcome under authoritative server adjudication.
          </p>
        </div>

        {/* Wallets & Telemetry Info */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 rounded bg-arcade-panel-raised border border-arcade-border/60 space-y-1">
            <div className="text-[10px] text-arcade-subtle uppercase tracking-wider">CREATOR WALLET</div>
            <div className="text-arcade-text font-semibold break-all">{challenge.creator_wallet}</div>
          </div>

          <div className="p-3 rounded bg-arcade-panel-raised border border-arcade-border/60 space-y-1">
            <div className="text-[10px] text-arcade-subtle uppercase tracking-wider">CHALLENGER WALLET</div>
            <div className="text-arcade-cyan font-semibold break-all">
              {challenge.accepted_by || 'Awaiting Challenger...'}
            </div>
          </div>
        </div>

        {/* Conditional Outcome Banners */}
        {challenge.status === 'CONDITION_MET' && (
          <div className="p-4 rounded bg-arcade-lime/10 border border-arcade-lime/60 space-y-2">
            <div className="flex items-center gap-2 text-arcade-lime font-mono font-bold text-sm">
              <CheckCircle2 className="w-5 h-5" />
              <span>BOUNTY READY FOR CLAIM</span>
            </div>
            <p className="text-xs font-mono text-arcade-muted">
              The Vault match resolved with the required condition. Winner eligible for payout:{' '}
              <span className="text-arcade-lime font-bold">{challenge.winner_wallet}</span>.
            </p>
            <div className="pt-2">
              <ArcadeButton
                variant="primary"
                size="md"
                className="w-full"
                isLoading={isProcessing}
                onClick={handleClaim}
              >
                CLAIM {challenge.bounty_amount.toFixed(1)} MON BOUNTY
              </ArcadeButton>
            </div>
            <div className="text-[10px] font-mono text-arcade-subtle text-center pt-1">
              [MOCK / LOCAL SETTLEMENT ENGINE — SIMULATION MODE]
            </div>
          </div>
        )}

        {challenge.status === 'CLAIMED' && (
          <div className="p-4 rounded bg-arcade-panel-raised border border-arcade-border space-y-2 text-xs font-mono">
            <div className="flex items-center gap-2 text-arcade-text font-bold">
              <Coins className="w-4 h-4 text-arcade-lime" />
              <span>SETTLEMENT COMPLETED</span>
            </div>
            <div className="text-arcade-subtle">
              Winner:{' '}
              <span className="text-arcade-lime font-semibold">{challenge.winner_wallet}</span>
            </div>
            {challenge.claim_tx_hash && (
              <div className="text-[11px] text-arcade-muted break-all">
                Settlement Tx: <span className="text-arcade-cyan">{challenge.claim_tx_hash}</span>
              </div>
            )}
            <div className="text-[10px] text-arcade-subtle pt-1">
              [VERIFIED BY BLOCKCHAIN SERVICE]
            </div>
          </div>
        )}

        {challenge.status === 'FAILED' && (
          <div className="p-4 rounded bg-arcade-danger/10 border border-arcade-danger/40 space-y-1 text-xs font-mono text-arcade-danger">
            <div className="flex items-center gap-2 font-bold">
              <AlertTriangle className="w-4 h-4" />
              <span>CONDITION FAILED</span>
            </div>
            <p className="text-arcade-muted text-[11px]">
              The match resolved without satisfying the required bounty condition. Escrow returns to
              the challenge creator.
            </p>
          </div>
        )}

        {/* Primary Action Button */}
        {challenge.status === 'OPEN' && (
          <div className="pt-2">
            <ArcadeButton
              variant="cyan"
              size="lg"
              className="w-full"
              isLoading={isProcessing}
              onClick={handleAccept}
            >
              ACCEPT CHALLENGE & LAUNCH VAULT
              <ArrowRight className="w-4 h-4 ml-2" />
            </ArcadeButton>
          </div>
        )}

        {challenge.status === 'ACTIVE' && challenge.match_id && (
          <div className="space-y-3 pt-2">
            <Link to={`/vault/${challenge.match_id}`} className="block">
              <ArcadeButton variant="cyan" size="lg" className="w-full">
                ENTER ACTIVE VAULT CHAMBER
                <ExternalLink className="w-4 h-4 ml-2" />
              </ArcadeButton>
            </Link>
            <div className="text-center text-[11px] font-mono text-arcade-subtle">
              Linked Match ID: <span className="text-arcade-text">{challenge.match_id}</span>
            </div>
          </div>
        )}
      </Panel>
    </PageContainer>
  );
};
