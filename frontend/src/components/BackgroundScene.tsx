import React from 'react';
import { ScreenVariant, SCREEN_ACCENTS } from '../styles/tokens';

interface BackgroundSceneProps {
  variant?: ScreenVariant;
  children?: React.ReactNode;
}

export const BackgroundScene: React.FC<BackgroundSceneProps> = ({ variant = 'home', children }) => {
  const accent = SCREEN_ACCENTS[variant] || 'lime';

  // Pure CSS retro arcade atmosphere: subtle marquee lighting, cabinet glow & micro-grid
  return (
    <div className="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden">
      {/* Ambient Cabinet Lighting */}
      <div className="absolute inset-0 pointer-events-none select-none overflow-hidden" aria-hidden="true">
        {/* Top Marquee/Cabinet Glow tailored to screen accent per DESIGN_SYSTEM.md */}
        {accent === 'lime' && (
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[720px] max-w-[90vw] h-[340px] bg-arcade-lime/5 blur-[100px] rounded-full" />
        )}
        {accent === 'pink' && (
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[720px] max-w-[90vw] h-[340px] bg-arcade-pink/5 blur-[100px] rounded-full" />
        )}
        {accent === 'cyan' && (
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[720px] max-w-[90vw] h-[340px] bg-arcade-cyan/5 blur-[100px] rounded-full" />
        )}

        {/* Subtle decorative grid floor/backdrop (restrained CSS) */}
        <div
          className="absolute inset-0 opacity-[0.025]"
          style={{
            backgroundImage: `linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)`,
            backgroundSize: '40px 40px',
          }}
        />

        {/* Faint vertical edge guide lines to give arcade cabinet framing */}
        <div className="hidden lg:block absolute left-8 top-0 bottom-0 w-px bg-arcade-border/20" />
        <div className="hidden lg:block absolute right-8 top-0 bottom-0 w-px bg-arcade-border/20" />
      </div>

      {/* Main Page Content */}
      <div className="relative z-20 w-full">{children}</div>
    </div>
  );
};
