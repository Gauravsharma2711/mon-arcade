import React from 'react';
import { Loader2, CheckCircle2, XCircle, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import { ArcadeButton } from './ArcadeButton';

export type TxStatus =
  | 'IDLE'
  | 'LOADING'
  | 'WAITING'
  | 'CONFIRMING'
  | 'SUCCESS'
  | 'FAILED'
  | 'RETRY';

interface TransactionStateProps {
  status: TxStatus;
  txHash?: string;
  errorMessage?: string;
  onRetry?: () => void;
  className?: string;
}

export const TransactionState: React.FC<TransactionStateProps> = ({
  status,
  txHash,
  errorMessage,
  onRetry,
  className = '',
}) => {
  if (status === 'IDLE') return null;

  const isPending = status === 'LOADING' || status === 'WAITING' || status === 'CONFIRMING';
  const isFailed = status === 'FAILED' || status === 'RETRY';
  const isSuccess = status === 'SUCCESS';

  const role = isFailed ? 'alert' : 'status';

  return (
    <div
      role={role}
      aria-live="polite"
      className={`animate-arcade-scale-in p-4 rounded border font-mono text-xs shadow-arcade-panel ${
        isPending
          ? 'bg-arcade-panel border-arcade-border text-arcade-muted'
          : isSuccess
          ? 'bg-arcade-panel border-arcade-lime/50 text-arcade-lime'
          : 'bg-arcade-panel border-arcade-danger/50 text-arcade-danger'
      } ${className}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {status === 'LOADING' && (
            <>
              <Loader2 className="w-4 h-4 animate-spin motion-reduce:animate-none text-arcade-lime" />
              <span className="font-semibold text-arcade-text tracking-wider uppercase">
                INITIATING TRANSACTION...
              </span>
            </>
          )}

          {status === 'WAITING' && (
            <>
              <Clock className="w-4 h-4 animate-pulse motion-reduce:animate-none text-arcade-warning" />
              <span className="font-semibold text-arcade-warning tracking-wider uppercase">
                WAITING FOR WALLET SIGNATURE...
              </span>
            </>
          )}

          {status === 'CONFIRMING' && (
            <>
              <Loader2 className="w-4 h-4 animate-spin motion-reduce:animate-none text-arcade-lime" />
              <span className="font-semibold text-arcade-text tracking-wider uppercase">
                CONFIRMING ON MONAD...
              </span>
            </>
          )}

          {status === 'SUCCESS' && (
            <>
              <CheckCircle2 className="w-4 h-4 text-arcade-lime" />
              <span className="font-semibold text-arcade-lime tracking-wider uppercase">
                TRANSACTION CONFIRMED
              </span>
            </>
          )}

          {status === 'FAILED' && (
            <>
              <XCircle className="w-4 h-4 text-arcade-danger" />
              <span className="font-semibold text-arcade-danger tracking-wider uppercase">
                TRANSACTION FAILED
              </span>
            </>
          )}

          {status === 'RETRY' && (
            <>
              <AlertCircle className="w-4 h-4 text-arcade-warning" />
              <span className="font-semibold text-arcade-warning tracking-wider uppercase">
                READY TO RETRY
              </span>
            </>
          )}
        </div>

        {/* Retry Button inside header if available */}
        {(status === 'FAILED' || status === 'RETRY') && onRetry && (
          <ArcadeButton
            variant="danger"
            size="sm"
            onClick={onRetry}
            className="shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            RETRY
          </ArcadeButton>
        )}
      </div>

      {txHash && (
        <div className="mt-2.5 pt-2 border-t border-arcade-border/50 text-[11px] text-arcade-subtle flex flex-wrap items-center gap-1.5">
          <span>TX HASH:</span>
          <span className="font-mono text-arcade-muted select-all break-all">
            {txHash}
          </span>
        </div>
      )}

      {errorMessage && (
        <p className="mt-2 text-arcade-danger text-xs leading-relaxed font-sans">
          {errorMessage}
        </p>
      )}
    </div>
  );
};
