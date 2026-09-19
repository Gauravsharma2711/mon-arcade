import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  maxWidth = 'md',
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-arcade-bg/85 backdrop-blur-sm animate-in fade-in duration-150 motion-reduce:animate-none"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        ref={modalRef}
        className={`w-full ${maxWClasses[maxWidth]} max-h-[90vh] bg-arcade-panel border border-arcade-border rounded-lg shadow-2xl overflow-hidden flex flex-col`}
      >
        {/* Modal Header */}
        <div className="px-4 sm:px-5 py-3 sm:py-4 border-b border-arcade-border flex items-center justify-between shrink-0">
          <h3 id="modal-title" className="font-display text-xs text-arcade-text tracking-wider uppercase">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="text-arcade-muted hover:text-arcade-text p-1.5 rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime"
            aria-label="Close modal dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-4 sm:p-6 overflow-y-auto max-h-[calc(90vh-130px)] font-sans text-sm text-arcade-text">
          {children}
        </div>

        {/* Optional Modal Footer */}
        {footer && (
          <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-arcade-border/80 bg-arcade-bg/50 font-mono text-xs shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
