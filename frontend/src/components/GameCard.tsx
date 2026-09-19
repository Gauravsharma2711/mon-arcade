import React from 'react';
import { Link } from 'react-router-dom';
import { ArcadeButton } from './ArcadeButton';
import { Users, Zap, Swords, Bot } from 'lucide-react';

interface GameCardProps {
  id: 'bluff' | 'vault';
  title: string;
  tagline: string;
  description: string;
  status?: 'LIVE' | 'DEVNET' | 'UPCOMING' | string;
  accent: 'pink' | 'cyan';
  playUrl: string;
  actionLabel?: string;
  playersCount?: string;
  potAmount?: string;
  mechanicInfo?: string;
  sponsorInfo?: string;
  visual?: React.ReactNode;
}

export const GameCard: React.FC<GameCardProps> = ({
  id,
  title,
  tagline,
  description,
  status = 'DEVNET',
  accent,
  playUrl,
  actionLabel = 'ENTER GAME',
  playersCount,
  potAmount,
  mechanicInfo,
  sponsorInfo,
  visual,
}) => {
  const isPink = accent === 'pink';

  const borderClass = isPink
    ? 'hover:border-arcade-pink/60 hover:shadow-arcade-pink'
    : 'hover:border-arcade-cyan/60 hover:shadow-arcade-cyan';

  const badgeClass = isPink
    ? 'text-arcade-pink border-arcade-pink/30 bg-arcade-pink/10'
    : 'text-arcade-cyan border-arcade-cyan/30 bg-arcade-cyan/10';

  const accentText = isPink ? 'text-arcade-pink' : 'text-arcade-cyan';

  // Dominant visual element: Anchors the card's visual identity
  const defaultVisual =
    id === 'bluff' ? (
      <div className="w-12 h-12 rounded-lg bg-arcade-bg border border-arcade-pink/40 flex items-center justify-center text-arcade-pink shadow-arcade-pink">
        <Swords className="w-6 h-6" />
      </div>
    ) : (
      <div className="w-12 h-12 rounded-lg bg-arcade-bg border border-arcade-cyan/40 flex items-center justify-center text-arcade-cyan shadow-arcade-cyan">
        <Bot className="w-6 h-6" />
      </div>
    );

  return (
    <div
      className={`rounded-lg bg-arcade-panel border border-arcade-border p-6 transition-all duration-200 flex flex-col justify-between ${borderClass} group motion-reduce:transition-none`}
    >
      <div>
        {/* Top Header: Dominant Visual & Status Badges */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            {visual || defaultVisual}
            <div>
              <span className={`text-[10px] font-mono font-bold tracking-widest px-2.5 py-0.5 rounded border ${badgeClass}`}>
                {status}
              </span>
              {mechanicInfo && (
                <span className="block text-[10px] font-mono text-arcade-subtle mt-1 uppercase tracking-wider">
                  {mechanicInfo}
                </span>
              )}
            </div>
          </div>

          {/* Telemetry (Players / Pot) */}
          <div className="flex flex-col items-end gap-1 text-xs font-mono text-arcade-subtle">
            {playersCount && (
              <span className="flex items-center gap-1">
                <Users className="w-3.5 h-3.5" />
                {playersCount}
              </span>
            )}
            {potAmount && (
              <span className={`flex items-center gap-1 font-bold ${accentText}`}>
                <Zap className="w-3.5 h-3.5" />
                {potAmount}
              </span>
            )}
          </div>
        </div>

        {/* Title & Tagline */}
        <h3 className="font-display text-lg tracking-wider text-arcade-text group-hover:text-white transition-colors mb-1.5">
          {title}
        </h3>
        <p className={`font-mono text-xs font-semibold tracking-wide ${accentText} mb-3 uppercase`}>
          {tagline}
        </p>

        {/* Description */}
        <p className="text-arcade-muted text-sm leading-relaxed mb-6 font-sans">
          {description}
        </p>
      </div>

      {/* Action Footer: One dominant, clear action */}
      <div className="pt-4 border-t border-arcade-border/50 flex items-center justify-between gap-3">
        <div className="text-[11px] font-mono text-arcade-subtle">
          {sponsorInfo ? (
            <span className="text-arcade-subtle">{sponsorInfo}</span>
          ) : (
            <span>INSTANT DUEL</span>
          )}
        </div>

        <Link
          to={playUrl}
          className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime rounded"
          tabIndex={-1}
        >
          <ArcadeButton variant={isPink ? 'pink' : 'cyan'} size="sm">
            {actionLabel}
          </ArcadeButton>
        </Link>
      </div>
    </div>
  );
};
