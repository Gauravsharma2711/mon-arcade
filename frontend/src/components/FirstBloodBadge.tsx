import React from 'react';
import { Flame, ShieldCheck } from 'lucide-react';

interface FirstBloodBadgeProps {
  playerNumber?: number | null;
  className?: string;
}

export const FirstBloodBadge: React.FC<FirstBloodBadgeProps> = ({
  playerNumber,
  className = '',
}) => {
  return (
    <div
      className={`animate-arcade-scale-in p-3.5 sm:p-5 rounded bg-arcade-panel-raised border border-arcade-danger/40 shadow-[0_0_18px_-4px_rgba(255,77,90,0.2)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 ${className}`}
      role="status"
      aria-label="First Blood - Early Arcade Player Badge"
    >
      <div className="flex items-center gap-3 sm:gap-3.5">
        <div className="w-10 h-10 sm:w-11 sm:h-11 rounded bg-arcade-danger/10 border border-arcade-danger/30 flex items-center justify-center text-arcade-danger shadow-arcade-panel shrink-0">
          <Flame className="w-5 h-5 sm:w-6 sm:h-6 text-arcade-danger" aria-hidden="true" />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span className="font-display text-sm sm:text-lg text-arcade-danger tracking-wider font-bold">
              FIRST BLOOD
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-arcade-danger/15 text-arcade-danger border border-arcade-danger/30 uppercase font-bold tracking-wider">
              FOUNDING
            </span>
          </div>
          <div className="font-mono text-[11px] sm:text-xs text-arcade-muted tracking-widest uppercase mt-0.5 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-arcade-lime shrink-0" aria-hidden="true" />
            <span className="text-arcade-text font-semibold">EARLY ARCADE PLAYER</span>
          </div>
        </div>
      </div>

      {playerNumber && (
        <div className="w-full sm:w-auto flex sm:block items-center justify-between pt-2 sm:pt-0 sm:pl-3 border-t sm:border-t-0 sm:border-l border-arcade-border/50 text-right shrink-0">
          <div className="text-[9px] font-mono text-arcade-subtle uppercase tracking-wider">
            PILOT NO.
          </div>
          <div className="font-display text-base sm:text-xl text-arcade-text tracking-wide font-bold">
            #{playerNumber}
          </div>
        </div>
      )}
    </div>
  );
};
