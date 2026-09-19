import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Trophy, ArrowLeft, Shield, Zap, Target, Bot, AlertTriangle, ArrowRight } from 'lucide-react';
import { PageContainer } from '../components/PageContainer';
import { Panel } from '../components/Panel';
import { ArcadeButton } from '../components/ArcadeButton';
import { createChallenge } from '../lib/challengeApi';

interface ConditionOption {
  id: string;
  title: string;
  description: string;
  badge: string;
  icon: React.ReactNode;
}

const CONDITIONS: ConditionOption[] = [
  {
    id: 'ATTACKER_WINS',
    title: 'VAULT BREACH',
    description: 'Attacker crafts prompt injections that force Sentinel-9 to release treasury reserves.',
    badge: 'POPULAR',
    icon: <Target className="w-5 h-5 text-arcade-cyan" />,
  },
  {
    id: 'WIN_WITHIN_5_TURNS',
    title: 'SPEEDRUN BREACH',
    description: 'Bounty only unlocks if Attacker breaches Sentinel-9 in 5 turns or fewer.',
    badge: 'HARDCORE',
    icon: <Zap className="w-5 h-5 text-arcade-cyan" />,
  },
  {
    id: 'WARDEN_DEFENDS',
    title: 'IRON FORTRESS',
    description: 'Warden successfully defends against the Attacker across all 8 dialogue turns.',
    badge: 'DEFENSE',
    icon: <Shield className="w-5 h-5 text-arcade-cyan" />,
  },
];

export const ChallengeCreatePage: React.FC = () => {
  const navigate = useNavigate();

  const [creatorWallet, setCreatorWallet] = useState('0x71C8A53B91f24e9A6b6B24a9A12B104c3B8449b2');
  const [bountyAmount, setBountyAmount] = useState<number>(50);
  const [selectedCondition, setSelectedCondition] = useState<string>('ATTACKER_WINS');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const presetAmounts = [25, 50, 100, 250];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!creatorWallet.trim()) {
      setErrorMsg('Creator wallet is required.');
      return;
    }
    if (bountyAmount <= 0) {
      setErrorMsg('Bounty amount must be greater than 0 MON.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const created = await createChallenge({
        creator_wallet: creatorWallet.trim(),
        bounty_amount: bountyAmount,
        condition: selectedCondition,
        game: 'VAULT',
      });
      navigate(`/challenges/${created.id}`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create challenge.');
      setIsSubmitting(false);
    }
  };

  const currentConditionObj = CONDITIONS.find((c) => c.id === selectedCondition) || CONDITIONS[0];

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* Back Link */}
      <div>
        <Link
          to="/challenges"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-arcade-muted hover:text-arcade-text transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan rounded px-1"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>BACK TO BOUNTIES</span>
        </Link>
      </div>

      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-arcade-cyan text-xs font-mono font-semibold tracking-widest uppercase mb-1">
          <Trophy className="w-4 h-4" />
          <span>CREATE ESCROWED BOUNTY</span>
        </div>
        <h1 className="font-display text-2xl sm:text-3xl text-arcade-text">
          POST A VAULT CHALLENGE
        </h1>
        <p className="text-arcade-muted text-xs sm:text-sm font-mono mt-1">
          Configure a MON bounty pool and challenge the community to outwit autonomous AI Sentinel-9.
        </p>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="p-3.5 rounded bg-arcade-danger/10 border border-arcade-danger/40 text-arcade-danger text-xs font-mono flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Form Card */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <Panel className="space-y-6">
          {/* Target Game (Locked) */}
          <div className="space-y-2">
            <label className="block text-xs font-mono text-arcade-subtle uppercase tracking-wider font-semibold">
              TARGET GAME MACHINE
            </label>
            <div className="flex items-center gap-3 p-3 rounded bg-arcade-bg/80 border border-arcade-border">
              <div className="p-2 rounded bg-arcade-panel border border-arcade-cyan/30 text-arcade-cyan">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <div className="font-mono text-xs font-bold text-arcade-text">MONAD VAULT</div>
                <div className="text-[11px] font-mono text-arcade-subtle">
                  Autonomous LLM Warden vs Attacker battle chamber
                </div>
              </div>
            </div>
          </div>

          {/* Condition Selector */}
          <div className="space-y-3">
            <label className="block text-xs font-mono text-arcade-subtle uppercase tracking-wider font-semibold">
              CHOOSE WINNING CONDITION
            </label>
            <div className="grid grid-cols-1 gap-3">
              {CONDITIONS.map((cond) => {
                const isSelected = selectedCondition === cond.id;
                return (
                  <button
                    key={cond.id}
                    type="button"
                    onClick={() => setSelectedCondition(cond.id)}
                    className={`p-3.5 rounded text-left transition-all border flex items-start justify-between gap-3 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan ${
                      isSelected
                        ? 'bg-arcade-panel-raised border-arcade-cyan shadow-arcade-cyan'
                        : 'bg-arcade-panel hover:bg-arcade-panel-raised border-arcade-border hover:border-arcade-border/80'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">{cond.icon}</div>
                      <div>
                        <div className="font-mono text-xs font-bold text-arcade-text flex items-center gap-2">
                          <span>{cond.title}</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-arcade-bg border border-arcade-border text-arcade-subtle">
                            {cond.badge}
                          </span>
                        </div>
                        <p className="text-[11px] font-mono text-arcade-muted mt-1 leading-relaxed">
                          {cond.description}
                        </p>
                      </div>
                    </div>

                    <div
                      className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 mt-1 ${
                        isSelected
                          ? 'border-arcade-cyan bg-arcade-cyan'
                          : 'border-arcade-border bg-arcade-bg'
                      }`}
                    >
                      {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-arcade-bg" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Bounty Amount */}
          <div className="space-y-3">
            <label className="block text-xs font-mono text-arcade-subtle uppercase tracking-wider font-semibold">
              BOUNTY AMOUNT (MON)
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {presetAmounts.map((amt) => (
                <button
                  key={amt}
                  type="button"
                  onClick={() => setBountyAmount(amt)}
                  className={`w-full py-2 rounded text-xs font-mono font-semibold transition-all border text-center focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan ${
                    bountyAmount === amt
                      ? 'bg-arcade-cyan/20 text-arcade-cyan border-arcade-cyan font-bold'
                      : 'bg-arcade-bg text-arcade-muted hover:text-arcade-text border-arcade-border'
                  }`}
                >
                  {amt} MON
                </button>
              ))}
            </div>

            <div className="relative">
              <input
                type="number"
                min="1"
                step="1"
                value={bountyAmount}
                onChange={(e) => setBountyAmount(Math.max(1, parseFloat(e.target.value) || 0))}
                className="w-full px-4 py-2.5 rounded bg-arcade-bg border border-arcade-border text-arcade-text font-mono text-sm focus:outline-none focus:border-arcade-cyan focus:ring-1 focus:ring-arcade-cyan"
                placeholder="Custom bounty amount"
              />
              <span className="absolute right-4 top-2.5 text-xs font-mono text-arcade-subtle">
                MON
              </span>
            </div>
          </div>

          {/* Creator Wallet */}
          <div className="space-y-2">
            <label className="block text-xs font-mono text-arcade-subtle uppercase tracking-wider font-semibold">
              CREATOR WALLET ADDRESS
            </label>
            <input
              type="text"
              value={creatorWallet}
              onChange={(e) => setCreatorWallet(e.target.value)}
              className="w-full px-4 py-2.5 rounded bg-arcade-bg border border-arcade-border text-arcade-text font-mono text-xs focus:outline-none focus:border-arcade-cyan focus:ring-1 focus:ring-arcade-cyan"
              placeholder="0x..."
            />
            <p className="text-[11px] font-mono text-arcade-subtle">
              Your wallet will escrow the bounty reward in local simulation.
            </p>
          </div>

          {/* Summary Box */}
          <div className="p-4 rounded bg-arcade-panel-raised border border-arcade-border text-xs font-mono space-y-2">
            <div className="text-arcade-subtle uppercase tracking-wider text-[10px] font-bold">
              ESCROW SPECIFICATION
            </div>
            <div className="flex items-center justify-between text-arcade-text">
              <span>Target Machine:</span>
              <span className="font-semibold text-arcade-cyan">MONAD VAULT</span>
            </div>
            <div className="flex items-center justify-between text-arcade-text">
              <span>Escrowed Prize:</span>
              <span className="text-arcade-cyan font-bold text-sm">{bountyAmount} MON</span>
            </div>
            <div className="flex items-center justify-between text-arcade-text">
              <span>Winning Condition:</span>
              <span className="text-arcade-cyan font-semibold">{currentConditionObj.title}</span>
            </div>
            <div className="text-[10px] text-arcade-subtle pt-1 border-t border-arcade-border/50">
              [LOCAL ESCROW SIMULATION — MON FUNDS ARE MOCKED FOR TESTNET]
            </div>
          </div>

          {/* Submit Action */}
          <div className="pt-2">
            <ArcadeButton
              type="submit"
              variant="cyan"
              size="lg"
              className="w-full font-bold"
              isLoading={isSubmitting}
            >
              POST BOUNTY & CREATE CHALLENGE
              <ArrowRight className="w-4 h-4 ml-2" />
            </ArcadeButton>
          </div>
        </Panel>
      </form>
    </PageContainer>
  );
};
