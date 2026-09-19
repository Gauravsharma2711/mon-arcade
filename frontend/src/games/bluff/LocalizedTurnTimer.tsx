import React, { useState, useEffect, useRef } from 'react';
import { Clock, AlertTriangle } from 'lucide-react';

interface LocalizedTurnTimerProps {
  initialSeconds: number;
  isActive: boolean;
  isPlayerTurn: boolean;
  onExpire?: () => void;
}

/**
 * Localized countdown timer for active Bluff duel turns.
 * Isolates second-by-second ticking to avoid unnecessary parent page re-renders.
 */
export const LocalizedTurnTimer: React.FC<LocalizedTurnTimerProps> = ({
  initialSeconds,
  isActive,
  isPlayerTurn,
  onExpire,
}) => {
  const [secondsLeft, setSecondsLeft] = useState<number>(Math.max(0, initialSeconds));
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  // Reconcile when server pushes a new authoritative seconds count
  useEffect(() => {
    setSecondsLeft(Math.max(0, initialSeconds));
  }, [initialSeconds]);

  // Localized tick interval
  useEffect(() => {
    if (!isActive || secondsLeft <= 0) return;

    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          onExpireRef.current?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isActive, secondsLeft]);

  const isUrgent = isActive && secondsLeft <= 5 && secondsLeft > 0;
  const isExpired = isActive && secondsLeft === 0;

  const formattedTime = `00:${secondsLeft.toString().padStart(2, '0')}`;

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded font-mono select-none transition-colors border ${
        isExpired
          ? 'bg-arcade-danger/10 border-arcade-danger text-arcade-danger'
          : isUrgent
          ? 'bg-arcade-danger/15 border-arcade-danger/70 text-arcade-danger shadow-[0_0_12px_rgba(255,77,90,0.2)]'
          : isPlayerTurn
          ? 'bg-arcade-pink/10 border-arcade-pink/40 text-arcade-pink'
          : 'bg-arcade-panel border-arcade-border text-arcade-text'
      }`}
      role="timer"
      aria-label={`Turn clock: ${secondsLeft} seconds remaining`}
      aria-atomic="true"
    >
      {isUrgent ? (
        <AlertTriangle className="w-4 h-4 text-arcade-danger animate-pulse motion-reduce:animate-none" />
      ) : (
        <Clock
          className={`w-4 h-4 ${
            isPlayerTurn ? 'text-arcade-pink' : 'text-arcade-subtle'
          }`}
        />
      )}

      <div className="flex flex-col">
        <span className="text-[9px] uppercase tracking-wider text-arcade-subtle font-bold leading-none">
          {isPlayerTurn ? 'YOUR DEADLINE' : 'TURN CLOCK'}
        </span>
        <span
          className={`font-display text-sm tracking-wider leading-tight ${
            isUrgent ? 'animate-pulse motion-reduce:animate-none text-arcade-danger' : ''
          }`}
        >
          {formattedTime}
        </span>
      </div>
    </div>
  );
};
