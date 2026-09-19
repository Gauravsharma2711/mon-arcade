import React from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { ArcadeHeader } from './ArcadeHeader';
import { BackgroundScene } from './BackgroundScene';

import { ScreenVariant } from '../styles/tokens';

export const ArcadeShell: React.FC = () => {
  const location = useLocation();

  // Determine accent/variant based on route per DESIGN_SYSTEM.md section 2
  let variant: ScreenVariant = 'home';
  if (location.pathname.startsWith('/bluff')) {
    variant = location.pathname.includes('/result') ? 'bluffResult' : 'bluff';
  } else if (location.pathname.startsWith('/vault')) {
    variant = location.pathname.includes('/result') ? 'vaultResult' : 'vault';
  } else if (location.pathname.startsWith('/sponsor')) {
    variant = 'sponsor';
  } else if (location.pathname.startsWith('/challenges')) {
    variant = 'vault';
  }

  return (
    <div className="min-h-screen bg-arcade-bg text-arcade-text flex flex-col relative selection:bg-arcade-lime selection:text-arcade-bg">
      {/* Skip to Content for Accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 bg-arcade-lime text-arcade-bg font-mono font-bold text-xs px-4 py-2 z-50 rounded shadow-arcade-lime focus:outline-none"
      >
        SKIP TO CONTENT
      </a>

      {/* Atmospheric CRT & Vignette Overlays (Decorative, non-blocking, behind interactive elements) */}
      <div className="crt-overlay" aria-hidden="true" />
      <div className="arcade-vignette" aria-hidden="true" />

      {/* Top Application Header */}
      <ArcadeHeader />

      {/* Content Canvas */}
      <div id="main-content" tabIndex={-1} className="flex-1 flex flex-col focus:outline-none">
        <BackgroundScene variant={variant}>
          <Outlet />
        </BackgroundScene>
      </div>

      {/* Restrained Arcade Shell Footer */}
      <footer className="mt-auto border-t border-arcade-border/80 bg-arcade-panel/40 py-5 px-4 sm:px-6 lg:px-8 relative z-20 font-mono text-xs text-arcade-subtle">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-arcade-lime" />
            <span className="text-arcade-text font-semibold tracking-wider">MON ARCADE</span>
            <span>&bull; FAST GAMES. STRANGE STRATEGIES. REAL MONAD ACTIONS.</span>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <Link to="/bluff" className="hover:text-arcade-pink transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-pink rounded px-1">
              BLUFF
            </Link>
            <Link to="/vault" className="hover:text-arcade-cyan transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan rounded px-1">
              VAULT
            </Link>
            <Link to="/challenges" className="hover:text-arcade-cyan transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan rounded px-1">
              BOUNTIES
            </Link>
            <Link to="/sponsor" className="hover:text-arcade-lime transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-lime rounded px-1">
              SPONSOR
            </Link>
            <Link to="/admin" className="hover:text-arcade-text transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-subtle rounded px-1">
              ADMIN
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};
