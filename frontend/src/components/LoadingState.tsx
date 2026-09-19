import React from 'react';
import { Loader2 } from 'lucide-react';

export type AsyncLoadingStatus =
  | 'LOADING'
  | 'CONNECTING'
  | 'WAITING_OPPONENT'
  | 'CONFIRMING_TRANSACTION'
  | 'WARDEN_THINKING'
  | 'ATTACKER_THINKING'
  | 'REVEALING_SECRET'
  | 'STREAMING_SSE'
  | string;

interface LoadingStateProps {
  status?: AsyncLoadingStatus;
  message?: string;
  subtext?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  status = 'LOADING',
  message,
  subtext = 'PLEASE STAND BY',
  className = '',
}) => {
  const defaultLabels: Record<string, string> = {
    LOADING: 'LOADING ARCADE DATA...',
    CONNECTING: 'CONNECTING TO MONAD...',
    WAITING_OPPONENT: 'WAITING FOR OPPONENT COMMITMENT...',
    CONFIRMING_TRANSACTION: 'CONFIRMING ON-CHAIN ACTION...',
    WARDEN_THINKING: 'WARDEN EVALUATING INTRUSION...',
    ATTACKER_THINKING: 'ATTACKER TRANSMITTING EXPLOIT...',
    REVEALING_SECRET: 'REVEALING SECRET NUMBER...',
    STREAMING_SSE: 'ESTABLISHING SSE TELEMETRY STREAM...',
  };

  const displayText = message || defaultLabels[status] || status;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center p-8 text-center font-mono select-none ${className}`}
    >
      <div className="relative mb-4">
        <Loader2 className="w-8 h-8 text-arcade-lime animate-spin motion-reduce:animate-none" />
      </div>
      <p className="text-xs font-semibold tracking-wider text-arcade-text uppercase">
        {displayText}
      </p>
      {subtext && (
        <p className="text-[11px] text-arcade-subtle mt-1.5 uppercase tracking-widest">
          {subtext}
        </p>
      )}
    </div>
  );
};
