import React from 'react';

interface PanelProps extends React.HTMLAttributes<HTMLDivElement> {
  raised?: boolean;
  selected?: boolean;
  accent?: 'lime' | 'cyan' | 'pink' | 'warning' | 'danger' | 'none';
  header?: React.ReactNode;
  footer?: React.ReactNode;
}

export const Panel: React.FC<PanelProps> = ({
  raised = false,
  selected = false,
  accent = 'none',
  header,
  footer,
  children,
  className = '',
  ...props
}) => {
  const bgClass = raised ? 'bg-arcade-panel-raised' : 'bg-arcade-panel';
  const borderWidthClass = selected ? 'border-2' : 'border';

  const accentBorders = {
    none: 'border-arcade-border',
    lime: selected ? 'border-arcade-lime shadow-arcade-lime' : 'border-arcade-border hover:border-arcade-lime/40',
    cyan: selected ? 'border-arcade-cyan shadow-arcade-cyan' : 'border-arcade-border hover:border-arcade-cyan/40',
    pink: selected ? 'border-arcade-pink shadow-arcade-pink' : 'border-arcade-border hover:border-arcade-pink/40',
    warning: selected ? 'border-arcade-warning' : 'border-arcade-border hover:border-arcade-warning/40',
    danger: selected ? 'border-arcade-danger' : 'border-arcade-border hover:border-arcade-danger/40',
  };

  return (
    <div
      className={`rounded ${borderWidthClass} ${bgClass} ${accentBorders[accent]} shadow-arcade-panel transition-colors motion-reduce:transition-none ${className}`}
      {...props}
    >
      {header && (
        <div className="px-5 py-3 border-b border-arcade-border flex items-center justify-between">
          {typeof header === 'string' ? (
            <h3 className="font-mono text-xs font-semibold tracking-wider text-arcade-muted uppercase">
              {header}
            </h3>
          ) : (
            header
          )}
        </div>
      )}
      <div className="p-5">{children}</div>
      {footer && (
        <div className="px-5 py-3 border-t border-arcade-border/60 bg-arcade-bg/40 flex items-center justify-between text-xs font-mono">
          {footer}
        </div>
      )}
    </div>
  );
};
