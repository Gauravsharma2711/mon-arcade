import React from 'react';

interface StatBarProps {
  label: string;
  value: number;
  max?: number;
  color?: 'lime' | 'cyan' | 'pink' | 'warning' | 'danger';
  showPercentage?: boolean;
}

export const StatBar: React.FC<StatBarProps> = ({
  label,
  value,
  max = 100,
  color = 'lime',
  showPercentage = false,
}) => {
  const safeMax = Math.max(1, max);
  const percentage = Math.min(100, Math.max(0, (value / safeMax) * 100));

  const fillColors = {
    lime: 'bg-arcade-lime shadow-arcade-lime',
    cyan: 'bg-arcade-cyan shadow-arcade-cyan',
    pink: 'bg-arcade-pink shadow-arcade-pink',
    warning: 'bg-arcade-warning',
    danger: 'bg-arcade-danger',
  };

  return (
    <div
      className="w-full font-mono text-xs"
      role="progressbar"
      aria-label={label}
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={safeMax}
    >
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-arcade-muted uppercase">{label}</span>
        <span className="text-arcade-text font-bold">
          {value}
          {showPercentage ? ` (${Math.round(percentage)}%)` : ` / ${safeMax}`}
        </span>
      </div>
      <div className="h-2 w-full bg-arcade-bg rounded-full overflow-hidden border border-arcade-border">
        <div
          className={`h-full rounded-full transition-all duration-300 motion-reduce:transition-none ${fillColors[color]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
