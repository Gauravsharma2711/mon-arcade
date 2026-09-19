import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Trophy, Plus, Shield, Zap, Target, ExternalLink, RefreshCw, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';
import { PageContainer } from '../components/PageContainer';
import { Panel } from '../components/Panel';
import { ArcadeButton } from '../components/ArcadeButton';
import { LoadingState } from '../components/LoadingState';
import {
  Challenge,
  ChallengeStatus,
  fetchChallenges,
  acceptChallenge,
} from '../lib/challengeApi';

export const ChallengesPage: React.FC = () => {
  const navigate = useNavigate();
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<ChallengeStatus | 'ALL'>('ALL');
  const [acceptingId, setAcceptingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadChallenges = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await fetchChallenges(filter === 'ALL' ? undefined : filter);
      setChallenges(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load challenges.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadChallenges();
  }, [filter]);

  const handleAccept = async (challenge: Challenge) => {
    setAcceptingId(challenge.id);
    setErrorMsg(null);
    try {
      const playerWallet = '0x71C8A53B91f24e9A6b6B24a9A12B104c3B8449b2';
      const updated = await acceptChallenge(challenge.id, playerWallet);
      if (updated.match_id) {
        navigate(`/vault/${updated.match_id}`);
      } else {
        await loadChallenges();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to accept challenge.');
      setAcceptingId(null);
    }
  };

  const getStatusBadge = (status: ChallengeStatus) => {
    switch (status) {
      case 'OPEN':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-arcade-lime/10 text-arcade-lime border border-arcade-lime/40">
            <span className="w-1.5 h-1.5 rounded-full bg-arcade-lime animate-pulse motion-reduce:animate-none" />
            OPEN
          </span>
        );
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-arcade-cyan/10 text-arcade-cyan border border-arcade-cyan/40">
            <span className="w-1.5 h-1.5 rounded-full bg-arcade-cyan animate-pulse motion-reduce:animate-none" />
            ACTIVE MATCH
          </span>
        );
      case 'CONDITION_MET':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-arcade-lime/20 text-arcade-lime border border-arcade-lime">
            <CheckCircle2 className="w-3 h-3 text-arcade-lime" />
            CLAIMABLE
          </span>
        );
      case 'CLAIMED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-arcade-panel-raised text-arcade-muted border border-arcade-border">
            CLAIMED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-arcade-danger/10 text-arcade-danger border border-arcade-danger/40">
            FAILED
          </span>
        );
    }
  };

  const getConditionIcon = (condition: string) => {
    if (condition.includes('5_TURNS')) return <Zap className="w-4 h-4 text-arcade-cyan" />;
    if (condition.includes('WARDEN')) return <Shield className="w-4 h-4 text-arcade-cyan" />;
    return <Target className="w-4 h-4 text-arcade-cyan" />;
  };

  return (
    <PageContainer maxWidth="xl" className="space-y-8">
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-arcade-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-arcade-cyan text-xs font-mono font-semibold tracking-widest uppercase mb-1">
            <Trophy className="w-4 h-4" />
            <span>COMMUNITY BOUNTY PROTOCOL</span>
          </div>
          <h1 className="font-display text-2xl sm:text-3xl text-arcade-text tracking-wide">
            ARCADE CHALLENGES
          </h1>
          <p className="text-arcade-muted text-xs sm:text-sm font-mono mt-1 max-w-2xl">
            Stake MON bounties on autonomous AI containment breaches. Accept existing community
            duels or escrow your own custom condition.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={loadChallenges}
            aria-label="Refresh challenges list"
            className="p-2.5 rounded bg-arcade-panel hover:bg-arcade-panel-raised border border-arcade-border text-arcade-subtle hover:text-arcade-text transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan shrink-0"
            title="Refresh List"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <Link to="/challenges/create" className="flex-1 sm:flex-initial">
            <ArcadeButton variant="cyan" size="md" className="w-full sm:w-auto">
              <Plus className="w-4 h-4 mr-1.5" />
              CREATE CHALLENGE
            </ArcadeButton>
          </Link>
        </div>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="p-3.5 rounded bg-arcade-danger/10 border border-arcade-danger/40 text-arcade-danger text-xs font-mono flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-arcade-border/60 pb-3 overflow-x-auto text-xs font-mono">
        {(['ALL', 'OPEN', 'ACTIVE', 'CONDITION_MET', 'CLAIMED', 'FAILED'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-3 py-1.5 rounded transition-all whitespace-nowrap focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan ${
              filter === tab
                ? 'bg-arcade-panel-raised text-arcade-cyan border border-arcade-cyan/40 font-bold'
                : 'text-arcade-subtle hover:text-arcade-text bg-arcade-panel/50 border border-transparent'
            }`}
          >
            {tab === 'CONDITION_MET' ? 'CLAIMABLE' : tab}
          </button>
        ))}
      </div>

      {/* Challenges Grid */}
      {isLoading ? (
        <div className="py-20">
          <LoadingState message="SCANNING BOUNTY REGISTRY..." subtext="Syncing verified Vault conditions" />
        </div>
      ) : challenges.length === 0 ? (
        <Panel className="text-center py-16">
          <Trophy className="w-10 h-10 text-arcade-subtle mx-auto mb-3" />
          <h3 className="font-display text-base text-arcade-text">NO CHALLENGES FOUND</h3>
          <p className="text-xs font-mono text-arcade-subtle mt-1 max-w-sm mx-auto">
            {filter !== 'ALL'
              ? `No challenges currently match the '${filter}' filter.`
              : 'Be the first contender to post a MON bounty for Sentinel-9 containment!'}
          </p>
          <div className="mt-5">
            <Link to="/challenges/create">
              <ArcadeButton variant="cyan" size="sm">
                POST FIRST BOUNTY
              </ArcadeButton>
            </Link>
          </div>
        </Panel>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {challenges.map((ch) => (
            <Panel
              key={ch.id}
              className="flex flex-col justify-between hover:border-arcade-cyan/50 transition-all duration-150 relative group"
            >
              <div className="space-y-4">
                {/* Header: Status and Game */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-arcade-cyan font-bold tracking-wider">
                    <span className="w-1.5 h-1.5 rounded-full bg-arcade-cyan" />
                    <span>MONAD VAULT</span>
                  </div>
                  {getStatusBadge(ch.status)}
                </div>

                {/* Bounty Display */}
                <div>
                  <div className="text-[10px] font-mono text-arcade-subtle uppercase tracking-wider">
                    ESCROWED BOUNTY
                  </div>
                  <div className="font-display text-2xl text-arcade-text tracking-wide flex items-baseline gap-1.5 mt-0.5">
                    <span className={ch.status === 'CONDITION_MET' ? 'text-arcade-lime font-bold' : 'text-arcade-cyan font-bold'}>
                      {ch.bounty_amount.toFixed(1)}
                    </span>
                    <span className="text-xs font-mono text-arcade-muted">MON</span>
                  </div>
                </div>

                {/* Condition Card */}
                <div className="p-3 rounded bg-arcade-bg/80 border border-arcade-border/80 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-mono font-semibold text-arcade-text">
                    {getConditionIcon(ch.condition)}
                    <span>{ch.condition.replace(/_/g, ' ')}</span>
                  </div>
                  <p className="text-[11px] font-mono text-arcade-subtle leading-relaxed">
                    {ch.condition_description}
                  </p>
                </div>

                {/* Wallets Telemetry */}
                <div className="pt-2 border-t border-arcade-border/50 text-[11px] font-mono space-y-1 text-arcade-subtle">
                  <div className="flex items-center justify-between">
                    <span>Creator:</span>
                    <span className="text-arcade-text font-semibold">
                      {ch.creator_wallet.slice(0, 6)}...{ch.creator_wallet.slice(-4)}
                    </span>
                  </div>
                  {ch.accepted_by && (
                    <div className="flex items-center justify-between">
                      <span>Challenger:</span>
                      <span className="text-arcade-cyan font-semibold">
                        {ch.accepted_by.slice(0, 6)}...{ch.accepted_by.slice(-4)}
                      </span>
                    </div>
                  )}
                  {ch.winner_wallet && (
                    <div className="flex items-center justify-between">
                      <span>Winner:</span>
                      <span className="text-arcade-lime font-semibold">
                        {ch.winner_wallet.slice(0, 6)}...{ch.winner_wallet.slice(-4)}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Button Footer */}
              <div className="mt-5 pt-3 border-t border-arcade-border/60">
                {ch.status === 'OPEN' ? (
                  <ArcadeButton
                    variant="cyan"
                    size="sm"
                    className="w-full font-bold"
                    isLoading={acceptingId === ch.id}
                    disabled={acceptingId !== null}
                    onClick={() => handleAccept(ch)}
                  >
                    ACCEPT & LAUNCH VAULT
                    <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </ArcadeButton>
                ) : ch.status === 'ACTIVE' && ch.match_id ? (
                  <Link to={`/vault/${ch.match_id}`} className="block">
                    <ArcadeButton variant="secondary" size="sm" className="w-full">
                      RESUME BATTLE CHAMBER
                      <ExternalLink className="w-3.5 h-3.5 ml-1.5" />
                    </ArcadeButton>
                  </Link>
                ) : (
                  <Link to={`/challenges/${ch.id}`} className="block">
                    <ArcadeButton
                      variant={ch.status === 'CONDITION_MET' ? 'primary' : 'secondary'}
                      size="sm"
                      className="w-full"
                    >
                      {ch.status === 'CONDITION_MET' ? 'CLAIM BOUNTY' : 'VIEW DETAILS'}
                      <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                    </ArcadeButton>
                  </Link>
                )}
              </div>
            </Panel>
          ))}
        </div>
      )}
    </PageContainer>
  );
};
