import React from 'react';
import { Loader2, Check, AlertCircle } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'tertiary' | 'danger' | 'cyan' | 'pink';
export type ButtonStatus = 'default' | 'loading' | 'success' | 'error';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ArcadeButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  status?: ButtonStatus;
  isLoading?: boolean; // Backwards-compatible convenience flag
}

export const ArcadeButton: React.FC<ArcadeButtonProps> = ({
  variant = 'primary',
  size = 'md',
  status = 'default',
  isLoading = false,
  children,
  className = '',
  disabled,
  ...props
}) => {
  const currentStatus: ButtonStatus = isLoading ? 'loading' : status;

  const baseClasses =
    'relative inline-flex items-center justify-center font-mono font-semibold tracking-wider transition-all duration-150 ' +
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime focus-visible:ring-offset-2 focus-visible:ring-offset-arcade-bg ' +
    'active:translate-y-[1px] active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none rounded select-none ' +
    'motion-reduce:transition-none motion-reduce:transform-none';

  const sizeClasses: Record<ButtonSize, string> = {
    sm: 'px-3 py-1.5 text-xs min-h-[36px]',
    md: 'px-5 py-2.5 text-sm min-h-[44px]',
    lg: 'px-7 py-3.5 text-base min-h-[48px]',
  };

  const variantClasses: Record<ButtonVariant, string> = {
    primary:
      'bg-arcade-lime text-arcade-bg hover:brightness-110 shadow-arcade-lime font-bold border border-transparent',
    secondary:
      'bg-arcade-panel hover:bg-arcade-panel-raised text-arcade-text border border-arcade-border hover:border-arcade-lime/60',
    tertiary:
      'bg-transparent hover:bg-arcade-panel text-arcade-muted hover:text-arcade-text border border-transparent',
    danger:
      'bg-arcade-danger text-white hover:brightness-110 shadow-[0_0_16px_-2px_rgba(255,77,90,0.3)] font-bold border border-transparent',
    cyan:
      'bg-arcade-cyan text-arcade-bg hover:brightness-110 shadow-arcade-cyan font-bold border border-transparent',
    pink:
      'bg-arcade-pink text-white hover:brightness-110 shadow-arcade-pink font-bold border border-transparent',
  };

  const statusClasses: Record<ButtonStatus, string> = {
    default: '',
    loading: 'cursor-wait opacity-90',
    success: 'bg-arcade-lime text-arcade-bg border-arcade-lime font-bold',
    error: 'bg-arcade-danger text-white border-arcade-danger font-bold',
  };

  return (
    <button
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${statusClasses[currentStatus]} ${className}`}
      disabled={disabled || currentStatus === 'loading'}
      aria-busy={currentStatus === 'loading'}
      {...props}
    >
      {currentStatus === 'loading' && (
        <span className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin motion-reduce:animate-none" />
          <span>LOADING...</span>
        </span>
      )}

      {currentStatus === 'success' && (
        <span className="flex items-center gap-1.5">
          <Check className="w-4 h-4 text-arcade-bg stroke-[3]" />
          <span>{children || 'SUCCESS'}</span>
        </span>
      )}

      {currentStatus === 'error' && (
        <span className="flex items-center gap-1.5">
          <AlertCircle className="w-4 h-4 text-white stroke-[2.5]" />
          <span>{children || 'FAILED'}</span>
        </span>
      )}

      {currentStatus === 'default' && children}
    </button>
  );
};
