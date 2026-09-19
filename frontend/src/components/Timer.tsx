import React from 'react';
import { Clock } from 'lucide-react';

interface TimerProps {
  seconds: number;
  label?: string;
  isUrgent?: boolean;
}

export const Timer: React.FC<TimerProps> = ({ seconds, label = 'TIME', isUrgent = false }) => {
  const safeSeconds = Math.max(0, seconds);
  const formattedTime = `${Math.floor(safeSeconds / 60)
    .toString()
    .padStart(2, '0')}:${(safeSeconds % 60).toString().padStart(2, '0')}`;

  return (
    <div
      className="flex items-center gap-2 font-mono select-none"
      role="timer"
      aria-label={`${label}: ${safeSeconds} seconds remaining`}
      aria-atomic="true"
    >
      <Clock
        className={`w-4 h-4 shrink-0 ${
          isUrgent ? 'text-arcade-danger animate-pulse motion-reduce:animate-none' : 'text-arcade-subtle'
        }`}
      />
      <div className="flex flex-col">
        {label && (
          <span className="text-[10px] text-arcade-subtle tracking-wider uppercase leading-tight">
            {label}
          </span>
        )}
        <span
          className={`font-display text-sm tracking-wider ${
            isUrgent ? 'text-arcade-danger animate-pulse motion-reduce:animate-none' : 'text-arcade-text'
          }`}
        >
          {formattedTime}
        </span>
      </div>
    </div>
  );
};
