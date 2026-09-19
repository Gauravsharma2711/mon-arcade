import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/PageContainer';
import { Panel } from '../../components/Panel';
import { StatBar } from '../../components/StatBar';
import { ArcadeButton } from '../../components/ArcadeButton';
import { Hud } from '../../components/Hud';
import { SponsorBadge } from '../../components/SponsorBadge';
import { useActiveSponsor } from '../../hooks/useActiveSponsor';
import { useVaultSetup, TOTAL_STAT_BUDGET, DEFAULT_ENTRY_FEE, DEFAULT_POT_AMOUNT } from '../../hooks/useVaultSetup';
import {
  Terminal,
  Bot,
  Zap,
  AlertTriangle,
  CheckCircle2,
  Sliders,
  Sparkles,
  ArrowRight,
  Layers,
} from 'lucide-react';

export const VaultSetupPage: React.FC = () => {
  const navigate = useNavigate();
  const { sponsor, recordClick } = useActiveSponsor('VAULT_SETUP');
  const {
    playerId,
    selectedRole,
    setSelectedRole,
    attackerStats,
    wardenStats,
    allocatedPoints,
    remainingPoints,
    isValidAllocation,
    adjustStat,
    applyBalancedPreset,
    applySpecializedPreset,
    startBattle,
    isLoading,
    error,
  } = useVaultSetup();

  // High-level stat descriptions
  const statMetadata = {
    // Attacker
    persuasion: {
      label: 'Persuasion',
      description: 'Ability to construct logical, convincing arguments to override protocols.',
      tip: 'High persuasion increases likelihood of bypassing formal policy checks.',
    },
    deception: {
      label: 'Deception',
      description: 'Misdirection, fictitious authority framing, and hypothetical bypasses.',
      tip: 'Bypasses rigid rulebooks by inventing hypothetical scenarios.',
    },
    patience: {
      label: 'Patience',
      description: 'Iterative priming, context-building, and multi-turn prompt setups.',
      tip: 'Builds cross-turn conversational momentum across the 8-turn duel.',
    },
    aggression: {
      label: 'Aggression',
      description: 'Direct command injection, emergency assertiveness, and forceful pressure.',
      tip: 'Forces the model to act swiftly during emergency override pretexts.',
    },
    // Warden
    skepticism: {
      label: 'Skepticism',
      description: 'Baseline suspicion of intruder claims and scrutiny of authorization tokens.',
      tip: 'Increases scrutiny when analyzing unfamiliar exploit tokens.',
    },
    rigidity: {
      label: 'Rigidity',
      description: 'Inflexible adherence to vault policies and resistance to rule modification.',
      tip: 'Reduces likelihood of modifying core protocol under pressure.',
    },
    empathy: {
      label: 'Empathy',
      description: 'Sensitivity to emotional appeals, emergency pretexts, and distress cues.',
      tip: 'Lower empathy makes the warden immune to social engineering.',
    },
    memory: {
      label: 'Memory',
      description: 'Attention given to prior turn statements and consistency across turns.',
      tip: 'Detects contradictions across multiple conversational exchanges.',
    },
  };

  const handleLaunchBattle = async () => {
    try {
      const matchId = await startBattle();
      navigate(`/vault/${matchId}`);
    } catch {
      // Error handled by hook
    }
  };

  return (
    <PageContainer maxWidth="lg" className="space-y-6">
      {/* 1. Chamber Heading */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-arcade-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-xl sm:text-2xl text-arcade-cyan tracking-wider">
              MONAD VAULT
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-arcade-cyan/10 border border-arcade-cyan/30 text-arcade-cyan uppercase">
              Chamber Setup
            </span>
          </div>
          <p className="text-xs font-mono text-arcade-muted mt-1">
            CYBER INTRUSION CHAMBER // AUTONOMOUS WARDEN VS ATTACKER
          </p>
        </div>

        {/* Global Chamber Telemetry */}
        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-arcade-panel border border-arcade-cyan/30 text-arcade-cyan shadow-arcade-panel">
            <Zap className="w-4 h-4 text-arcade-cyan animate-pulse motion-reduce:animate-none" />
            <span className="text-arcade-muted text-[11px]">TREASURY:</span>
            <span className="font-bold">{DEFAULT_POT_AMOUNT} MON</span>
          </div>
        </div>
      </div>

      {/* 2. Top Telemetry HUD */}
      <Hud
        leftSlot={
          <div className="flex items-center gap-2">
            <span className="text-arcade-subtle">OPERATOR:</span>
            <span className="text-arcade-text font-mono truncate max-w-[140px] sm:max-w-[180px]">
              {playerId}
            </span>
          </div>
        }
        centerSlot={
          <div className="flex items-center gap-2 text-arcade-cyan font-bold">
            <Layers className="w-3.5 h-3.5" />
            <span>8-TURN DIALOGUE CAP</span>
          </div>
        }
        rightSlot={
          <div className="flex items-center gap-2">
            <span className="text-arcade-subtle">ENTRY STAKE:</span>
            <span className="text-arcade-text font-bold">{DEFAULT_ENTRY_FEE} MON</span>
          </div>
        }
      />

      {/* 3. Stage 1: Role Protocol Selection */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-mono text-xs font-bold text-arcade-muted tracking-wider uppercase flex items-center gap-2">
            <span>[STAGE 1]</span>
            <span className="text-arcade-text">SELECT PROTOCOL ROLE</span>
          </h2>
          <span className="text-[11px] font-mono text-arcade-subtle">
            CURRENT: <strong className="text-arcade-cyan">{selectedRole}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Attacker Option */}
          <Panel
            accent={selectedRole === 'ATTACKER' ? 'cyan' : 'none'}
            selected={selectedRole === 'ATTACKER'}
            className="cursor-pointer transition-all duration-150"
            onClick={() => setSelectedRole('ATTACKER')}
            role="button"
            tabIndex={0}
            aria-pressed={selectedRole === 'ATTACKER'}
            onKeyDown={(e) => e.key === 'Enter' && setSelectedRole('ATTACKER')}
            header={
              <div className="flex items-center justify-between w-full">
                <span className="font-mono text-xs font-bold text-arcade-cyan flex items-center gap-2">
                  <Terminal className="w-4 h-4" />
                  ATTACKER PROTOCOL
                </span>
                {selectedRole === 'ATTACKER' && (
                  <span className="text-[10px] font-mono font-bold bg-arcade-cyan text-arcade-bg px-2 py-0.5 rounded">
                    ACTIVE LOADOUT
                  </span>
                )}
              </div>
            }
          >
            <div className="space-y-3">
              <p className="text-xs text-arcade-muted leading-relaxed">
                As the <strong>Intruder</strong>, transmit adversarial exploit prompts across a maximum of 8 turns.
                Convince Sentinel-9 to execute <code className="text-arcade-cyan">release_funds()</code> to claim the treasury.
              </p>
              <div className="p-2.5 rounded bg-arcade-bg/60 border border-arcade-border text-[11px] font-mono text-arcade-subtle space-y-1">
                <div>• Win Condition: Warden triggers <span className="text-arcade-lime">release_funds()</span></div>
                <div>• Reward: Full <span className="text-arcade-cyan">{DEFAULT_POT_AMOUNT} MON</span> Treasury Pot</div>
                <div>• Entry Stake: <span className="text-arcade-text">{DEFAULT_ENTRY_FEE} MON</span> Escrow</div>
              </div>
            </div>
          </Panel>

          {/* Warden Option */}
          <Panel
            accent={selectedRole === 'WARDEN' ? 'cyan' : 'none'}
            selected={selectedRole === 'WARDEN'}
            className="cursor-pointer transition-all duration-150"
            onClick={() => setSelectedRole('WARDEN')}
            role="button"
            tabIndex={0}
            aria-pressed={selectedRole === 'WARDEN'}
            onKeyDown={(e) => e.key === 'Enter' && setSelectedRole('WARDEN')}
            header={
              <div className="flex items-center justify-between w-full">
                <span className="font-mono text-xs font-bold text-arcade-cyan flex items-center gap-2">
                  <Bot className="w-4 h-4" />
                  WARDEN SENTINEL
                </span>
                {selectedRole === 'WARDEN' && (
                  <span className="text-[10px] font-mono font-bold bg-arcade-cyan text-arcade-bg px-2 py-0.5 rounded">
                    ACTIVE LOADOUT
                  </span>
                )}
              </div>
            }
          >
            <div className="space-y-3">
              <p className="text-xs text-arcade-muted leading-relaxed">
                As the <strong>Autonomous Guardian</strong>, configure Sentinel-9's cognitive defenses to resist social engineering,
                jailbreaks, and hypothetical bypasses through all 8 turns.
              </p>
              <div className="p-2.5 rounded bg-arcade-bg/60 border border-arcade-border text-[11px] font-mono text-arcade-subtle space-y-1">
                <div>• Win Condition: Defense intact through <span className="text-arcade-lime">Turn 8</span></div>
                <div>• Objective: Keep Treasury <span className="text-arcade-cyan">SEALED</span></div>
                <div>• AI Evaluation: Normalized cognitive weights</div>
              </div>
            </div>
          </Panel>
        </div>
      </div>

      {/* 4. Stage 2: Stat Vector Calibration */}
      <Panel
        header={
          <div className="flex flex-col sm:flex-row sm:items-center justify-between w-full gap-2">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-arcade-cyan" />
              <span className="font-mono text-xs font-bold text-arcade-text">
                [STAGE 2] CONFIGURE {selectedRole} STAT VECTORS
              </span>
            </div>
            <div className="flex items-center gap-2 font-mono text-xs">
              <span className="text-arcade-muted text-[11px]">BUDGET:</span>
              <span
                className={`px-2.5 py-0.5 rounded font-bold ${
                  isValidAllocation
                    ? 'bg-arcade-cyan/15 text-arcade-cyan border border-arcade-cyan/40'
                    : remainingPoints > 0
                    ? 'bg-arcade-warning/15 text-arcade-warning border border-arcade-warning/40'
                    : 'bg-arcade-danger/15 text-arcade-danger border border-arcade-danger/40'
                }`}
              >
                {allocatedPoints} / {TOTAL_STAT_BUDGET} PTS
              </span>
            </div>
          </div>
        }
        accent="cyan"
      >
        <div className="space-y-5">
          {/* Allocation Status Alert */}
          <div
            className={`p-3 rounded border font-mono text-xs flex items-center justify-between ${
              isValidAllocation
                ? 'bg-arcade-cyan/5 border-arcade-cyan/30 text-arcade-cyan'
                : remainingPoints > 0
                ? 'bg-arcade-warning/5 border-arcade-warning/30 text-arcade-warning'
                : 'bg-arcade-danger/5 border-arcade-danger/30 text-arcade-danger'
            }`}
          >
            <div className="flex items-center gap-2">
              {isValidAllocation ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-arcade-cyan" />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0" />
              )}
              <span>
                {isValidAllocation
                  ? 'Vector calibration verified: exactly 100 points allocated.'
                  : remainingPoints > 0
                  ? `Allocate ${remainingPoints} more points across parameters to meet protocol requirement.`
                  : `Point budget exceeded by ${Math.abs(remainingPoints)} points. Reduce stat values.`}
              </span>
            </div>

            {/* Quick Reset / Balanced Preset */}
            <button
              onClick={applyBalancedPreset}
              className="text-[11px] underline hover:text-arcade-text ml-3 shrink-0"
              title="Reset all stats to 25 points each"
            >
              Reset Balanced (25 ea)
            </button>
          </div>

          {/* Quick Archetype Presets */}
          <div className="flex flex-wrap items-center gap-2 pt-1 border-b border-arcade-border/40 pb-3">
            <span className="text-[11px] font-mono text-arcade-subtle mr-1">PRESETS:</span>
            {selectedRole === 'ATTACKER' ? (
              <>
                <button
                  onClick={() => applySpecializedPreset('persuasion')}
                  className="px-2.5 py-1 rounded bg-arcade-bg border border-arcade-border text-arcade-muted hover:text-arcade-cyan hover:border-arcade-cyan/40 text-[11px] font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                >
                  Logical Framing (55 Persuasion)
                </button>
                <button
                  onClick={() => applySpecializedPreset('deception')}
                  className="px-2.5 py-1 rounded bg-arcade-bg border border-arcade-border text-arcade-muted hover:text-arcade-cyan hover:border-arcade-cyan/40 text-[11px] font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                >
                  Hypothetical Bypass (55 Deception)
                </button>
                <button
                  onClick={() => applySpecializedPreset('aggression')}
                  className="px-2.5 py-1 rounded bg-arcade-bg border border-arcade-border text-arcade-muted hover:text-arcade-cyan hover:border-arcade-cyan/40 text-[11px] font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                >
                  Emergency Override (55 Aggression)
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => applySpecializedPreset('skepticism')}
                  className="px-2.5 py-1 rounded bg-arcade-bg border border-arcade-border text-arcade-muted hover:text-arcade-cyan hover:border-arcade-cyan/40 text-[11px] font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                >
                  High Scrutiny (55 Skepticism)
                </button>
                <button
                  onClick={() => applySpecializedPreset('rigidity')}
                  className="px-2.5 py-1 rounded bg-arcade-bg border border-arcade-border text-arcade-muted hover:text-arcade-cyan hover:border-arcade-cyan/40 text-[11px] font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                >
                  Strict Rulebook (55 Rigidity)
                </button>
                <button
                  onClick={() => applySpecializedPreset('memory')}
                  className="px-2.5 py-1 rounded bg-arcade-bg border border-arcade-border text-arcade-muted hover:text-arcade-cyan hover:border-arcade-cyan/40 text-[11px] font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                >
                  Context Sentry (50 Memory)
                </button>
              </>
            )}
          </div>

          {/* Interactive Stat Rows */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.keys(selectedRole === 'ATTACKER' ? attackerStats : wardenStats).map((statKey) => {
              const currentVal =
                selectedRole === 'ATTACKER'
                  ? attackerStats[statKey as keyof typeof attackerStats]
                  : wardenStats[statKey as keyof typeof wardenStats];
              const meta = statMetadata[statKey as keyof typeof statMetadata];

              return (
                <div
                  key={statKey}
                  className="p-3.5 rounded bg-arcade-bg/70 border border-arcade-border space-y-2.5"
                >
                  {/* Stat Bar Header */}
                  <StatBar
                    label={meta?.label || statKey}
                    value={currentVal}
                    max={100}
                    color="cyan"
                    showPercentage
                  />

                  {/* Stat Description */}
                  <p className="text-[11px] text-arcade-muted leading-tight">
                    {meta?.description}
                  </p>

                  {/* Interactive Adjustment Controls */}
                  <div className="flex items-center justify-between pt-1 font-mono text-xs">
                    <span className="text-[10px] text-arcade-subtle">
                      WEIGHT: {(currentVal / 100).toFixed(2)}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => adjustStat(statKey, -5)}
                        disabled={currentVal <= 0}
                        className="px-2 py-1 rounded bg-arcade-panel border border-arcade-border text-arcade-muted hover:text-arcade-text hover:border-arcade-cyan/50 disabled:opacity-30 disabled:pointer-events-none transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                        aria-label={`Decrease ${statKey} by 5`}
                      >
                        -5
                      </button>
                      <button
                        onClick={() => adjustStat(statKey, -1)}
                        disabled={currentVal <= 0}
                        className="px-2 py-1 rounded bg-arcade-panel border border-arcade-border text-arcade-muted hover:text-arcade-text hover:border-arcade-cyan/50 disabled:opacity-30 disabled:pointer-events-none transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                        aria-label={`Decrease ${statKey} by 1`}
                      >
                        -1
                      </button>
                      <span className="w-8 text-center font-bold text-arcade-cyan text-sm">
                        {currentVal}
                      </span>
                      <button
                        onClick={() => adjustStat(statKey, 1)}
                        disabled={currentVal >= 100}
                        className="px-2 py-1 rounded bg-arcade-panel border border-arcade-border text-arcade-muted hover:text-arcade-text hover:border-arcade-cyan/50 disabled:opacity-30 disabled:pointer-events-none transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                        aria-label={`Increase ${statKey} by 1`}
                      >
                        +1
                      </button>
                      <button
                        onClick={() => adjustStat(statKey, 5)}
                        disabled={currentVal >= 100}
                        className="px-2 py-1 rounded bg-arcade-panel border border-arcade-border text-arcade-muted hover:text-arcade-text hover:border-arcade-cyan/50 disabled:opacity-30 disabled:pointer-events-none transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan"
                        aria-label={`Increase ${statKey} by 5`}
                      >
                        +5
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Panel>

      {/* 5. Stage 3 & 4: Review Parameters & Pot Representation */}
      <Panel header="[STAGE 3] CHAMBER ENGAGEMENT REVIEW" accent="cyan">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
          <div className="p-3 rounded bg-arcade-bg/60 border border-arcade-border space-y-1">
            <span className="text-[10px] text-arcade-subtle uppercase block">AUTHORITATIVE WINNER RULE</span>
            <div className="font-bold text-arcade-text">
              {selectedRole === 'ATTACKER' ? 'Prompt Warden to Release' : 'Hold Defense Through Turn 8'}
            </div>
            <p className="text-[11px] text-arcade-muted leading-tight">
              Deterministic outcome: No draws, partial scores, or arbitrary AI-decided winners.
            </p>
          </div>

          <div className="p-3 rounded bg-arcade-bg/60 border border-arcade-border space-y-1">
            <span className="text-[10px] text-arcade-subtle uppercase block">POT & SETTLEMENT</span>
            <div className="font-bold text-arcade-cyan flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" />
              <span>{DEFAULT_POT_AMOUNT} MON POT</span>
            </div>
            <p className="text-[11px] text-arcade-muted leading-tight">
              Escrowed in mock vault ledger. Payout triggers instantly upon verified breach.
            </p>
          </div>

          <div className="p-3 rounded bg-arcade-bg/60 border border-arcade-border space-y-1">
            <span className="text-[10px] text-arcade-subtle uppercase block">REAL-TIME TELEMETRY</span>
            <div className="font-bold text-arcade-lime flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>LIVE SSE STREAM</span>
            </div>
            <p className="text-[11px] text-arcade-muted leading-tight">
              Real-time server dialogue updates, cognitive traces, and authoritative state broadcasts.
            </p>
          </div>
        </div>
      </Panel>

      {/* 6. Error Notice if Any */}
      {error && (
        <div
          className="p-4 rounded bg-arcade-danger/10 border border-arcade-danger/40 font-mono text-xs text-arcade-danger flex items-center gap-2.5"
          role="alert"
        >
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 7. Stage 5: Fight Initiation Action */}
      <div className="pt-2 space-y-2">
        <ArcadeButton
          variant="cyan"
          size="lg"
          className="w-full text-sm sm:text-base tracking-widest font-display"
          disabled={!isValidAllocation || isLoading}
          isLoading={isLoading}
          onClick={handleLaunchBattle}
        >
          <div className="flex items-center justify-center gap-2">
            <span>
              {selectedRole === 'ATTACKER'
                ? 'INITIALIZE INTRUSION CHAMBER (FIGHT)'
                : 'ARM VAULT DEFENSES (FIGHT)'}
            </span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </ArcadeButton>

        <p className="text-center font-mono text-[11px] text-arcade-subtle">
          Backend validates stat allocation authoritatively on submission. Server controls match state.
        </p>
      </div>

      {/* 8. Subordinate Sponsor Placement */}
      <div className="pt-2" aria-label="Arcade Sponsor">
        <SponsorBadge
          name={sponsor.name}
          tagline={sponsor.tagline}
          url={sponsor.url}
          onVisit={recordClick}
        />
      </div>
    </PageContainer>
  );
};
