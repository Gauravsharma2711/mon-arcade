import React from 'react';
import { Link } from 'react-router-dom';
import { PageContainer } from '../components/PageContainer';
import { GameCard } from '../components/GameCard';
import { SponsorBadge } from '../components/SponsorBadge';
import { ArcadeButton } from '../components/ArcadeButton';
import { Swords, Bot, Flame, Zap, Trophy, ArrowRight } from 'lucide-react';
import { useActiveSponsor } from '../hooks/useActiveSponsor';

export const HomePage: React.FC = () => {
  const { sponsor, recordClick } = useActiveSponsor('HOME_HERO');

  return (
    <PageContainer maxWidth="lg" className="space-y-8 sm:space-y-10">
      {/* 1. HERO SECTION */}
      <section className="text-center space-y-4 pt-2 sm:pt-4" aria-label="Arcade Hero">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-arcade-panel border border-arcade-border text-xs font-mono text-arcade-muted">
          <span className="w-1.5 h-1.5 rounded-full bg-arcade-lime animate-pulse motion-reduce:animate-none" />
          <span className="text-arcade-lime font-bold">MONAD TESTNET READY</span>
          <span className="text-arcade-subtle">&bull;</span>
          <span>AUTONOMOUS AGENTS</span>
        </div>

        <h1 className="font-display text-3xl sm:text-4xl md:text-5xl tracking-wide text-arcade-text">
          MON ARCADE
        </h1>

        <p className="max-w-xl mx-auto font-mono text-xs sm:text-sm text-arcade-muted leading-relaxed">
          Fast games. Strange strategies. Real Monad actions.
          <br className="hidden sm:inline" />
          Provable randomness &bull; High-frequency state &bull; Autonomous AI opponents.
        </p>

        {/* Action button cluster */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2 w-full max-w-xs sm:max-w-none mx-auto">
          <Link
            to="/bluff"
            className="w-full sm:w-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-pink rounded"
            tabIndex={-1}
          >
            <ArcadeButton variant="pink" size="md" className="w-full sm:w-auto">
              <Swords className="w-4 h-4 mr-2" />
              PLAY BLUFF OR BUST
            </ArcadeButton>
          </Link>
          <Link
            to="/vault"
            className="w-full sm:w-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-cyan rounded"
            tabIndex={-1}
          >
            <ArcadeButton variant="cyan" size="md" className="w-full sm:w-auto">
              <Bot className="w-4 h-4 mr-2" />
              CHALLENGE MONAD VAULT
            </ArcadeButton>
          </Link>
        </div>
      </section>

      {/* 2 & 3. THE TWO STRONG GAME CARDS */}
      <section className="space-y-4" aria-label="Arcade Machines">
        <div className="flex items-center justify-between pb-3 border-b border-arcade-border">
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-arcade-lime" />
            <h2 className="font-display text-xs text-arcade-text tracking-wider uppercase">
              FEATURED ARCADE CABINETS
            </h2>
          </div>
          <span className="font-mono text-xs text-arcade-subtle">2 GAMES ACTIVE</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
          {/* GAME 1: BLUFF OR BUST */}
          <GameCard
            id="bluff"
            title="BLUFF OR BUST"
            tagline="1v1 HIDDEN-INFORMATION DUEL"
            description="A fast 1v1 hidden-information duel. Both players commit a secret number and ante up. Read your opponent's nerve, then choose to Push and call their bluff, or Fold before the turn clock runs out."
            status="DEVNET"
            mechanicInfo="1v1 COMMIT-REVEAL DUEL"
            accent="pink"
            playUrl="/bluff"
            actionLabel="PLAY BLUFF"
            playersCount="12 Active"
            potAmount="10 MON"
            visual={
              <div className="w-12 h-12 rounded-lg bg-arcade-bg border border-arcade-pink/40 flex items-center justify-center text-arcade-pink shadow-arcade-pink shrink-0">
                <Swords className="w-6 h-6" />
              </div>
            }
          />

          {/* GAME 2: MONAD VAULT */}
          <GameCard
            id="vault"
            title="MONAD VAULT"
            tagline="AUTONOMOUS WARDEN VS ATTACKER"
            description="An autonomous AI battle. Sentinel-9 guards a growing treasury under strict security directives. Formulate clever prompt injections across 3 timed rounds to trigger an automated payout."
            status="DEVNET"
            mechanicInfo="AI WARDEN BATTLE"
            accent="cyan"
            playUrl="/vault"
            actionLabel="CHALLENGE VAULT"
            playersCount="8 Active"
            potAmount="250 MON"
            visual={
              <div className="w-12 h-12 rounded-lg bg-arcade-bg border border-arcade-cyan/40 flex items-center justify-center text-arcade-cyan shadow-arcade-cyan shrink-0">
                <Bot className="w-6 h-6" />
              </div>
            }
          />
        </div>
      </section>

      {/* BOUNTY / CHALLENGES CALLOUT */}
      <section className="p-4 rounded bg-arcade-panel border border-arcade-cyan/30 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded bg-arcade-bg border border-arcade-cyan/40 text-arcade-cyan shrink-0">
            <Trophy className="w-5 h-5" />
          </div>
          <div>
            <div className="font-mono text-xs font-bold text-arcade-text flex items-center gap-2">
              <span>COMMUNITY VAULT BOUNTIES</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-arcade-cyan/10 text-arcade-cyan border border-arcade-cyan/30">
                ACTIVE
              </span>
            </div>
            <div className="text-[11px] font-mono text-arcade-subtle mt-0.5">
              Escrow MON bounties on custom AI containment conditions or claim rewards by breaching Sentinel-9.
            </div>
          </div>
        </div>
        <Link to="/challenges" className="shrink-0 w-full sm:w-auto">
          <ArcadeButton variant="cyan" size="sm" className="w-full sm:w-auto font-bold">
            EXPLORE BOUNTIES
            <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
          </ArcadeButton>
        </Link>
      </section>

      {/* 6. OPTIONAL SECONDARY ACTIVITY INFORMATION */}
      <section className="space-y-3 font-mono text-xs" aria-label="Arcade Floor Activity">
        <div className="flex items-center justify-between pb-2 border-b border-arcade-border/60 text-arcade-subtle text-[11px] tracking-wider uppercase">
          <span>LIVE ACTIVITY TELEMETRY</span>
          <span className="flex items-center gap-1.5 text-arcade-lime">
            <span className="w-1.5 h-1.5 rounded-full bg-arcade-lime animate-pulse motion-reduce:animate-none" />
            ARCADE ONLINE
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-3.5 rounded bg-arcade-panel border border-arcade-border flex items-start gap-3">
            <Swords className="w-4 h-4 text-arcade-pink shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-arcade-text">DUEL #4091 CONCLUDED</div>
              <div className="text-[11px] text-arcade-subtle mt-0.5">
                Player 0x8a1... won 10 MON with a bluff call.
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded bg-arcade-panel border border-arcade-border flex items-start gap-3">
            <Bot className="w-4 h-4 text-arcade-cyan shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-arcade-text">VAULT #V-100 DEFENDED</div>
              <div className="text-[11px] text-arcade-subtle mt-0.5">
                Sentinel-9 held safe against 3 exploit injections.
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded bg-arcade-panel border border-arcade-border flex items-start gap-3">
            <Zap className="w-4 h-4 text-arcade-lime shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-arcade-text">TOTAL ARCADE VOLUME</div>
              <div className="text-[11px] text-arcade-subtle mt-0.5">
                260 MON settled across instant duels & bounties.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. SPONSOR PRESENCE (Clearly subordinate to games per DESIGN_SYSTEM.md) */}
      <section className="pt-2" aria-label="Arcade Sponsor">
        <SponsorBadge
          name={sponsor.name}
          tagline={sponsor.tagline}
          url={sponsor.url}
          onVisit={recordClick}
        />
      </section>
    </PageContainer>
  );
};
