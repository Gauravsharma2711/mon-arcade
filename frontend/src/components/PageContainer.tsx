import React from 'react';

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}

export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  className = '',
  maxWidth = 'lg',
}) => {
  const maxWClasses = {
    sm: 'max-w-xl',
    md: 'max-w-3xl',
    lg: 'max-w-5xl',
    xl: 'max-w-7xl',
    full: 'max-w-full',
  };

  return (
    <main
      className={`mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10 w-full ${maxWClasses[maxWidth]} ${className}`}
    >
      {children}
    </main>
  );
};
