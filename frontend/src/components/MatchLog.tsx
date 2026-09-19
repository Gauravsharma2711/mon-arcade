import React from 'react';

export interface LogEntry {
  id: string;
  timestamp: string;
  text: string;
  type?: 'neutral' | 'accent' | 'warning' | 'danger' | 'cyan' | 'lime';
}

interface MatchLogProps {
  entries: LogEntry[];
  title?: string;
  className?: string;
  maxHeight?: string;
}

export const MatchLog: React.FC<MatchLogProps> = ({
  entries,
  title = 'MATCH LOG',
  className = '',
  maxHeight = 'max-h-48',
}) => {
  return (
    <div
      className={`bg-arcade-panel border border-arcade-border rounded p-4 flex flex-col font-mono text-xs ${className}`}
      role="log"
      aria-label={title}
      aria-live="polite"
    >
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-arcade-border text-arcade-subtle text-[10px] tracking-wider uppercase">
        <span>{title}</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-arcade-cyan animate-pulse motion-reduce:animate-none" />
          LIVE FEED
        </span>
      </div>

      <div className={`overflow-y-auto ${maxHeight} space-y-1.5 scrollbar-thin`}>
        {entries.length === 0 ? (
          <p className="text-arcade-subtle italic py-2">No actions recorded yet.</p>
        ) : (
          entries.map((entry) => {
            const colorClass = {
              neutral: 'text-arcade-muted',
              accent: 'text-arcade-lime',
              warning: 'text-arcade-warning',
              danger: 'text-arcade-danger',
              cyan: 'text-arcade-cyan',
              lime: 'text-arcade-lime font-bold',
            }[entry.type || 'neutral'];

            return (
              <div key={entry.id} className="flex items-start gap-2 leading-relaxed">
                <span className="text-arcade-subtle text-[10px] shrink-0 select-none">
                  [{entry.timestamp}]
                </span>
                <span className={`${colorClass} break-words`}>{entry.text}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
