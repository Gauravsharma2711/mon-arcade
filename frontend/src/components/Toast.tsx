import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const Toast: React.FC<ToastProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full px-4 sm:px-0"
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => {
        const borderColors = {
          info: 'border-arcade-border text-arcade-text',
          success: 'border-arcade-lime/60 text-arcade-lime',
          warning: 'border-arcade-warning/60 text-arcade-warning',
          error: 'border-arcade-danger/60 text-arcade-danger',
        };

        const Icon = {
          info: Info,
          success: CheckCircle2,
          warning: AlertTriangle,
          error: AlertCircle,
        }[toast.type];

        return (
          <div
            key={toast.id}
            role="status"
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded bg-arcade-panel border ${borderColors[toast.type]} shadow-2xl animate-in fade-in slide-in-from-bottom-2 duration-150 motion-reduce:animate-none`}
          >
            <Icon className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="font-mono text-xs font-semibold tracking-wide text-arcade-text">
                {toast.title}
              </p>
              {toast.message && (
                <p className="text-xs text-arcade-muted mt-1 leading-snug font-sans">
                  {toast.message}
                </p>
              )}
            </div>
            <button
              onClick={() => onDismiss(toast.id)}
              className="text-arcade-muted hover:text-arcade-text p-1 shrink-0 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime transition-colors"
              aria-label="Dismiss notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
