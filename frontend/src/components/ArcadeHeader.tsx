import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Gamepad2, Wallet, ChevronDown, Menu, X, Swords, Bot, Megaphone, Check, Copy, Trophy } from 'lucide-react';

export const ArcadeHeader: React.FC = () => {
  const location = useLocation();
  const [mockAddress, setMockAddress] = useState<string | null>(null);
  const [isPlayMenuOpen, setIsPlayMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const playMenuRef = useRef<HTMLDivElement>(null);

  // Close menus on route change
  useEffect(() => {
    setIsPlayMenuOpen(false);
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Handle click outside to close PLAY dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (playMenuRef.current && !playMenuRef.current.contains(event.target as Node)) {
        setIsPlayMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleWallet = () => {
    if (mockAddress) {
      setMockAddress(null);
    } else {
      setMockAddress('0x71C8...49b2');
    }
  };

  const copyAddress = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (mockAddress) {
      navigator.clipboard?.writeText?.('0x71C8A53B91f24e9A6b6B24a9A12B104c3B8449b2');
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 1500);
    }
  };

  const isPlayActive = location.pathname.startsWith('/bluff') || location.pathname.startsWith('/vault');
  const isSponsorActive = location.pathname.startsWith('/sponsor');
  const isChallengesActive = location.pathname.startsWith('/challenges');
  const isHomeActive = location.pathname === '/';

  return (
    <header className="sticky top-0 z-50 w-full bg-arcade-bg/95 backdrop-blur-md border-b border-arcade-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        
        {/* Branding */}
        <Link
          to="/"
          className="flex items-center gap-2.5 sm:gap-3 group shrink-0 rounded p-1 -ml-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime"
          aria-label="Mon Arcade Home"
        >
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded bg-arcade-panel border border-arcade-border flex items-center justify-center text-arcade-lime group-hover:border-arcade-lime/60 group-hover:shadow-arcade-lime transition-all">
            <Gamepad2 className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div>
            <div className="font-display text-xs sm:text-sm tracking-wider text-arcade-text group-hover:text-arcade-lime transition-colors">
              MON ARCADE
            </div>
            <div className="text-[9px] sm:text-[10px] text-arcade-subtle tracking-widest font-mono uppercase">
              MONAD DAPP
            </div>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-1.5" aria-label="Main Navigation">
          {/* Home / Arcade */}
          <Link
            to="/"
            className={`px-3 py-1.5 text-xs font-mono tracking-wider transition-colors rounded border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime ${
              isHomeActive
                ? 'text-arcade-lime bg-arcade-panel border-arcade-lime/30'
                : 'text-arcade-muted hover:text-arcade-text hover:bg-arcade-panel border-transparent'
            }`}
          >
            ARCADE
          </Link>

          {/* PLAY Dropdown */}
          <div className="relative" ref={playMenuRef}>
            <button
              onClick={() => setIsPlayMenuOpen((prev) => !prev)}
              aria-expanded={isPlayMenuOpen}
              aria-haspopup="true"
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono tracking-wider transition-colors rounded border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime ${
                isPlayActive || isPlayMenuOpen
                  ? 'text-arcade-text bg-arcade-panel border-arcade-border'
                  : 'text-arcade-muted hover:text-arcade-text hover:bg-arcade-panel border-transparent'
              }`}
            >
              <span>PLAY</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-150 ${isPlayMenuOpen ? 'rotate-180 text-arcade-lime' : ''}`} />
            </button>

            {/* PLAY Popover Menu */}
            {isPlayMenuOpen && (
              <div
                className="absolute top-full left-0 mt-2 w-64 rounded-lg bg-arcade-panel border border-arcade-border shadow-2xl p-2 z-50 space-y-1 font-mono text-xs animate-in fade-in slide-in-from-top-2 duration-150"
                role="menu"
              >
                <div className="px-2.5 py-1 text-[10px] text-arcade-subtle uppercase tracking-wider font-semibold border-b border-arcade-border/50 mb-1">
                  CHOOSE MACHINE
                </div>

                {/* Bluff or Bust */}
                <Link
                  to="/bluff"
                  role="menuitem"
                  className="flex items-start gap-3 p-2.5 rounded hover:bg-arcade-panel-raised border border-transparent hover:border-arcade-pink/30 group transition-all"
                >
                  <div className="p-1.5 rounded bg-arcade-bg border border-arcade-border text-arcade-pink group-hover:border-arcade-pink/50">
                    <Swords className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="font-bold text-arcade-text group-hover:text-arcade-pink transition-colors">
                      BLUFF OR BUST
                    </div>
                    <div className="text-[11px] text-arcade-subtle">
                      1v1 Hidden Duel &bull; Fast Staking
                    </div>
                  </div>
                </Link>

                {/* Monad Vault */}
                <Link
                  to="/vault"
                  role="menuitem"
                  className="flex items-start gap-3 p-2.5 rounded hover:bg-arcade-panel-raised border border-transparent hover:border-arcade-cyan/30 group transition-all"
                >
                  <div className="p-1.5 rounded bg-arcade-bg border border-arcade-border text-arcade-cyan group-hover:border-arcade-cyan/50">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="font-bold text-arcade-text group-hover:text-arcade-cyan transition-colors">
                      MONAD VAULT
                    </div>
                    <div className="text-[11px] text-arcade-subtle">
                      Autonomous AI Warden Battle
                    </div>
                  </div>
                </Link>
              </div>
            )}
          </div>

          {/* BOUNTIES / CHALLENGES */}
          <Link
            to="/challenges"
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono tracking-wider transition-colors rounded border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-cyan ${
              isChallengesActive
                ? 'text-arcade-cyan bg-arcade-panel border-arcade-cyan/30'
                : 'text-arcade-muted hover:text-arcade-text hover:bg-arcade-panel border-transparent'
            }`}
          >
            <Trophy className="w-3.5 h-3.5" />
            <span>BOUNTIES</span>
          </Link>

          {/* SPONSOR */}
          <Link
            to="/sponsor"
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono tracking-wider transition-colors rounded border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime ${
              isSponsorActive
                ? 'text-arcade-lime bg-arcade-panel border-arcade-lime/30'
                : 'text-arcade-muted hover:text-arcade-text hover:bg-arcade-panel border-transparent'
            }`}
          >
            <Megaphone className="w-3.5 h-3.5" />
            <span>SPONSOR</span>
          </Link>
        </nav>

        {/* Header Right: Devnet Badge & Compact Wallet */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Devnet Status Indicator */}
          <div
            className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-arcade-panel border border-arcade-border text-[11px] font-mono text-arcade-muted"
            title="Monad Network Status"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-arcade-lime animate-pulse" />
            <span>DEVNET</span>
          </div>

          {/* Compact Wallet Button (Restrained & Non-Dominant) */}
          <div className="flex items-center gap-1">
            <button
              onClick={toggleWallet}
              className={`flex items-center gap-2 px-3 py-1.5 sm:py-2 rounded bg-arcade-panel hover:bg-arcade-panel-raised border text-xs font-mono transition-all duration-150 min-h-[40px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime ${
                mockAddress
                  ? 'border-arcade-border text-arcade-text hover:border-arcade-lime/60'
                  : 'border-arcade-border text-arcade-muted hover:text-arcade-text hover:border-arcade-border'
              }`}
              aria-label={mockAddress ? `Connected as ${mockAddress}` : 'Connect Wallet'}
            >
              <Wallet className={`w-3.5 h-3.5 ${mockAddress ? 'text-arcade-lime' : 'text-arcade-subtle'}`} />
              <span className="tracking-wide">
                {mockAddress ? mockAddress : 'CONNECT'}
              </span>
            </button>

            {/* Quick Copy Action if connected */}
            {mockAddress && (
              <button
                onClick={copyAddress}
                className="hidden sm:flex items-center justify-center p-2 rounded bg-arcade-panel hover:bg-arcade-panel-raised border border-arcade-border text-arcade-subtle hover:text-arcade-text min-h-[40px] min-w-[40px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime"
                title={isCopied ? 'Address Copied!' : 'Copy Address'}
                aria-label="Copy wallet address"
              >
                {isCopied ? <Check className="w-3.5 h-3.5 text-arcade-lime" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            )}
          </div>

          {/* Mobile Menu Toggle Button (Min 44x44px touch target) */}
          <button
            onClick={() => setIsMobileMenuOpen((prev) => !prev)}
            aria-expanded={isMobileMenuOpen}
            aria-label={isMobileMenuOpen ? 'Close Menu' : 'Open Menu'}
            className="md:hidden flex items-center justify-center w-11 h-11 rounded bg-arcade-panel border border-arcade-border text-arcade-muted hover:text-arcade-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime transition-colors"
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {isMobileMenuOpen && (
        <div
          className="md:hidden border-t border-arcade-border bg-arcade-bg/98 px-4 py-4 space-y-4 font-mono text-xs animate-in fade-in slide-in-from-top-2 duration-150 shadow-2xl"
          role="region"
          aria-label="Mobile Navigation"
        >
          <div className="text-[10px] text-arcade-subtle uppercase tracking-wider font-semibold px-2">
            NAVIGATION
          </div>

          <div className="space-y-1">
            <Link
              to="/"
              className={`flex items-center justify-between px-3 py-2.5 rounded border transition-colors min-h-[44px] ${
                isHomeActive
                  ? 'text-arcade-lime bg-arcade-panel border-arcade-lime/40'
                  : 'text-arcade-text bg-arcade-panel border-arcade-border'
              }`}
            >
              <span className="font-bold">ARCADE HOME</span>
              <span className="text-[10px] text-arcade-subtle">&rarr;</span>
            </Link>

            <div className="pt-2 pb-1 text-[10px] text-arcade-subtle uppercase tracking-wider font-semibold px-2">
              PLAY GAMES
            </div>

            <Link
              to="/bluff"
              className="flex items-center justify-between px-3 py-2.5 rounded bg-arcade-panel border border-arcade-border hover:border-arcade-pink/40 text-arcade-text min-h-[44px]"
            >
              <div className="flex items-center gap-2">
                <Swords className="w-4 h-4 text-arcade-pink" />
                <span>BLUFF OR BUST</span>
              </div>
              <span className="text-[10px] text-arcade-pink font-bold border border-arcade-pink/30 px-1.5 py-0.5 rounded bg-arcade-pink/10">
                1v1
              </span>
            </Link>

            <Link
              to="/vault"
              className="flex items-center justify-between px-3 py-2.5 rounded bg-arcade-panel border border-arcade-border hover:border-arcade-cyan/40 text-arcade-text min-h-[44px]"
            >
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-arcade-cyan" />
                <span>MONAD VAULT</span>
              </div>
              <span className="text-[10px] text-arcade-cyan font-bold border border-arcade-cyan/30 px-1.5 py-0.5 rounded bg-arcade-cyan/10">
                AI
              </span>
            </Link>

            <div className="pt-2 pb-1 text-[10px] text-arcade-subtle uppercase tracking-wider font-semibold px-2">
              COMMUNITY BOUNTIES
            </div>

            <Link
              to="/challenges"
              className={`flex items-center justify-between px-3 py-2.5 rounded border transition-colors min-h-[44px] ${
                isChallengesActive
                  ? 'text-arcade-cyan bg-arcade-panel border-arcade-cyan/40'
                  : 'text-arcade-text bg-arcade-panel border-arcade-border'
              }`}
            >
              <div className="flex items-center gap-2">
                <Trophy className="w-4 h-4 text-arcade-cyan" />
                <span>ARCADE CHALLENGES</span>
              </div>
              <span className="text-[10px] text-arcade-cyan font-bold border border-arcade-cyan/30 px-1.5 py-0.5 rounded bg-arcade-cyan/10">
                MON
              </span>
            </Link>

            <div className="pt-2 pb-1 text-[10px] text-arcade-subtle uppercase tracking-wider font-semibold px-2">
              MONAD SPONSOR
            </div>

            <Link
              to="/sponsor"
              className={`flex items-center justify-between px-3 py-2.5 rounded border transition-colors min-h-[44px] ${
                isSponsorActive
                  ? 'text-arcade-lime bg-arcade-panel border-arcade-lime/40'
                  : 'text-arcade-text bg-arcade-panel border-arcade-border'
              }`}
            >
              <div className="flex items-center gap-2">
                <Megaphone className="w-4 h-4 text-arcade-lime" />
                <span>SPONSOR PORTAL</span>
              </div>
              <span className="text-[10px] text-arcade-subtle">&rarr;</span>
            </Link>
          </div>

          {/* Mobile Network & Wallet Details */}
          <div className="pt-3 border-t border-arcade-border flex items-center justify-between text-[11px] text-arcade-subtle px-1">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-arcade-lime animate-pulse" />
              <span>MONAD DEVNET</span>
            </div>
            <span>FAST EXECUTION</span>
          </div>
        </div>
      )}
    </header>
  );
};
