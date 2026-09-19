import React from 'react';

interface HudProps {
  leftSlot?: React.ReactNode;
  centerSlot?: React.ReactNode;
  rightSlot?: React.ReactNode;
  className?: string;
}

export const Hud: React.FC<HudProps> = ({ leftSlot, centerSlot, rightSlot, className = '' }) => {
  return (
    <div
      className={`w-full bg-arcade-panel-raised border border-arcade-border rounded px-3 sm:px-4 py-2.5 sm:py-3 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 sm:gap-3 shadow-arcade-panel font-mono text-xs ${className}`}
      role="region"
      aria-label="Game HUD"
    >
      <div className="flex items-center gap-2 sm:gap-4 w-full sm:w-auto justify-between sm:justify-start min-w-0">
        {leftSlot}
      </div>
      {centerSlot && (
        <div className="flex items-center gap-2 sm:gap-4 justify-center py-1 sm:py-0 border-y sm:border-y-0 border-arcade-border/30 sm:border-none">
          {centerSlot}
        </div>
      )}
      <div className="flex items-center gap-2 sm:gap-4 w-full sm:w-auto justify-between sm:justify-end min-w-0">
        {rightSlot}
      </div>
    </div>
  );
};
