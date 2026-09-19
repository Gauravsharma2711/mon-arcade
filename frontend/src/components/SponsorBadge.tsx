import React from 'react';
import { ExternalLink } from 'lucide-react';

interface SponsorBadgeProps {
  name?: string;
  tagline?: string;
  url?: string;
  className?: string;
  onVisit?: () => void;
}

export const SponsorBadge: React.FC<SponsorBadgeProps> = ({
  name = 'MON ARCADE',
  tagline = 'POWERED BY MONAD HIGH-THROUGHPUT EXECUTION',
  url,
  className = '',
  onVisit,
}) => {
  return (
    <div
      className={`rounded border border-arcade-border/80 bg-arcade-panel/60 px-3.5 py-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 sm:gap-4 text-xs font-mono backdrop-blur-sm ${className}`}
      role="complementary"
      aria-label="Arcade Sponsor"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10px] text-arcade-subtle tracking-widest uppercase border border-arcade-border px-1.5 py-0.5 rounded shrink-0">
          SPONSOR
        </span>
        <span className="font-semibold text-arcade-text tracking-wide">{name}</span>
        <span className="text-arcade-subtle text-[11px]">&bull; {tagline}</span>
      </div>

      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={onVisit}
          className="text-arcade-muted hover:text-arcade-lime transition-colors flex items-center gap-1 text-[11px] shrink-0 rounded px-1 py-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime"
          aria-label={`Visit sponsor ${name} (opens in new tab)`}
        >
          <span>VISIT</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      )}
    </div>
  );
};
