import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/PageContainer';
import { Panel } from '../../components/Panel';
import { ArcadeButton } from '../../components/ArcadeButton';
import { LoadingState } from '../../components/LoadingState';
import { Modal } from '../../components/Modal';
import { SponsorBadge } from '../../components/SponsorBadge';
import { useActiveSponsor } from '../../hooks/useActiveSponsor';
import { useBluffLobby } from '../../hooks/useBluffLobby';
import {
  Swords,
  Plus,
  ArrowRight,
  RefreshCw,
  Copy,
  Check,
  QrCode,
  XCircle,
  EyeOff,
  AlertCircle,
  User,
  Bot,
} from 'lucide-react';

export const BluffLobbyPage: React.FC = () => {
  const navigate = useNavigate();
  const { sponsor, recordClick } = useActiveSponsor('BLUFF_LOBBY');
  const {
    playerId,
    switchPlayer,
    openLobbies,
    createdMatch,
    status,
    error,
    refreshLobbies,
    createDuel,
    joinDuel,
    spawnSimulatedOpponent,
    cancelDuel,
  } = useBluffLobby();

  // Create Duel Modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedStake, setSelectedStake] = useState<number>(5);
  const [selectedSecret, setSelectedSecret] = useState<number>(7);
  const [isCreating, setIsCreating] = useState(false);

  // Join Duel Modal state
  const [joiningMatchId, setJoiningMatchId] = useState<string | null>(null);
  const [joinSecret, setJoinSecret] = useState<number>(5);
  const [isJoining, setIsJoining] = useState(false);

  // Manual Match ID Input state
  const [manualMatchId, setManualMatchId] = useState('');

  // Copy share link feedback
  const [isCopied, setIsCopied] = useState(false);

  // Identity switcher toggle
  const [showIdentitySwitch, setShowIdentitySwitch] = useState(false);
  const [customIdInput, setCustomIdInput] = useState('');

  // Handle Create Duel
  const handleCreateSubmit = async () => {
    try {
      setIsCreating(true);
      await createDuel(selectedStake, selectedSecret);
      setIsCreateModalOpen(false);
      // Stay on lobby page while waiting for opponent (or auto-enter if opponent joined)
    } catch {
      // Error handled in hook
    } finally {
      setIsCreating(false);
    }
  };

  // Handle Join Duel
  const handleJoinSubmit = async () => {
    if (!joiningMatchId) return;
    try {
      setIsJoining(true);
      await joinDuel(joiningMatchId, joinSecret);
      navigate(`/bluff/${joiningMatchId}`);
    } catch {
      // Error handled in hook
    } finally {
      setIsJoining(false);
    }
  };

  // Copy Duel Share Link
  const copyShareLink = (matchId: string) => {
    const url = `${window.location.origin}/bluff/${matchId}`;
    navigator.clipboard?.writeText?.(url);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* 1. Page Title & Identity Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-arcade-border gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Swords className="w-5 h-5 text-arcade-pink" />
            <h1 className="font-display text-xl text-arcade-pink tracking-wider uppercase">
              BLUFF OR BUST
            </h1>
          </div>
          <p className="text-xs font-mono text-arcade-muted mt-1">
            1v1 HIDDEN-INFORMATION DUEL LOBBY &bull; COMMIT-REVEAL SHOWDOWN
          </p>
        </div>

        {/* Player Identity Badge */}
        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded bg-arcade-panel border border-arcade-border text-xs font-mono flex items-center gap-2">
            <User className="w-3.5 h-3.5 text-arcade-pink" />
            <span className="text-arcade-subtle">PLAYER:</span>
            <span className="text-arcade-text font-bold tracking-wider">
              {playerId ? `${playerId.slice(0, 6)}...${playerId.slice(-4)}` : '0xPLAYER'}
            </span>
          </div>

          <button
            onClick={() => setShowIdentitySwitch(!showIdentitySwitch)}
            className="text-[11px] font-mono text-arcade-subtle hover:text-arcade-pink underline px-1 py-0.5"
            title="Switch player address to test multiplayer duels locally"
          >
            SWITCH
          </button>
        </div>
      </div>

      {/* Local Multiplayer Switcher Tool */}
      {showIdentitySwitch && (
        <div className="p-3 bg-arcade-panel-raised border border-arcade-pink/40 rounded flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono">
          <span className="text-arcade-subtle">LOCAL MULTIPLAYER IDENTITY:</span>
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <button
              onClick={() => switchPlayer('0xplayer_alice_1')}
              className="px-2 py-1 bg-arcade-panel border border-arcade-border rounded hover:border-arcade-pink text-arcade-text"
            >
              ALICE
            </button>
            <button
              onClick={() => switchPlayer('0xplayer_bob_2')}
              className="px-2 py-1 bg-arcade-panel border border-arcade-border rounded hover:border-arcade-pink text-arcade-text"
            >
              BOB
            </button>
            <input
              type="text"
              placeholder="Custom 0x..."
              value={customIdInput}
              onChange={(e) => setCustomIdInput(e.target.value)}
              className="px-2 py-1 bg-arcade-bg border border-arcade-border rounded text-arcade-text flex-1 sm:w-28 text-[11px]"
            />
            {customIdInput && (
              <button
                onClick={() => {
                  switchPlayer(customIdInput);
                  setCustomIdInput('');
                }}
                className="px-2 py-1 bg-arcade-pink text-white font-bold rounded"
              >
                SET
              </button>
            )}
          </div>
        </div>
      )}

      {/* Error Alert if any */}
      {error && (
        <div
          role="alert"
          className="p-4 rounded bg-arcade-danger/10 border border-arcade-danger/60 text-arcade-danger text-xs font-mono flex items-center justify-between gap-3"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={refreshLobbies}
            className="underline hover:text-white shrink-0"
          >
            RETRY
          </button>
        </div>
      )}

      {/* 2. Primary Actions Area (Create / Join By ID) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Create Duel Trigger */}
        <div className="p-5 rounded bg-arcade-panel border border-arcade-pink/40 hover:border-arcade-pink/60 shadow-arcade-panel flex flex-col justify-between space-y-4 transition-colors">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-display text-sm text-arcade-pink tracking-wider">
                HOST A DUEL
              </span>
              <span className="text-[10px] font-mono text-arcade-pink border border-arcade-pink/30 px-2 py-0.5 rounded bg-arcade-pink/10">
                1v1 SHOWDOWN
              </span>
            </div>
            <p className="text-xs font-sans text-arcade-muted leading-relaxed">
              Post your stake and cryptographically lock a secret card. Opponent cannot see your value until reveal.
            </p>
          </div>
          <ArcadeButton
            variant="pink"
            size="md"
            className="w-full"
            onClick={() => setIsCreateModalOpen(true)}
            disabled={status === 'CREATING DUEL...' || Boolean(createdMatch && createdMatch.status === 'WAITING')}
          >
            <Plus className="w-4 h-4 mr-1.5" />
            CREATE DUEL
          </ArcadeButton>
        </div>

        {/* Join by Code / Direct ID */}
        <div className="p-5 rounded bg-arcade-panel border border-arcade-border flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-display text-sm text-arcade-text tracking-wider">
                JOIN DUEL BY ID
              </span>
              <span className="text-[10px] font-mono text-arcade-subtle border border-arcade-border px-2 py-0.5 rounded">
                DIRECT CODE
              </span>
            </div>
            <p className="text-xs font-sans text-arcade-muted leading-relaxed">
              Have a friend's duel match code? Enter it below to join the match station directly.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="e.g. bluff_ace4e5d3"
              value={manualMatchId}
              onChange={(e) => setManualMatchId(e.target.value.trim())}
              aria-label="Enter Match ID to join directly"
              className="flex-1 px-3 py-2 text-xs font-mono bg-arcade-bg border border-arcade-border rounded text-arcade-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-pink"
            />
            <ArcadeButton
              variant="secondary"
              size="sm"
              disabled={!manualMatchId}
              onClick={() => {
                setJoiningMatchId(manualMatchId);
              }}
            >
              JOIN <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </ArcadeButton>
          </div>
        </div>
      </div>

      {/* 3. Created Match / Waiting for Opponent Banner */}
      {createdMatch && createdMatch.status === 'WAITING' && (
        <Panel
          header={
            <div className="flex items-center justify-between w-full">
              <span className="text-arcade-pink font-bold">YOUR ACTIVE DUEL STATION</span>
              <span className="text-[10px] text-arcade-pink animate-pulse">
                WAITING FOR OPPONENT...
              </span>
            </div>
          }
          accent="pink"
          selected
        >
          <div className="space-y-4 py-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded bg-arcade-bg border border-arcade-pink/30">
              <div className="space-y-1">
                <div className="font-mono text-xs text-arcade-subtle">DUEL ID:</div>
                <div className="font-mono text-sm font-bold text-arcade-pink">
                  {createdMatch.id}
                </div>
                <div className="text-[11px] font-mono text-arcade-muted flex items-center gap-2 mt-1">
                  <span>STAKE: <strong className="text-arcade-text">{createdMatch.stake_amount} MON</strong></span>
                  <span>&bull;</span>
                  <span>POT: <strong className="text-arcade-text">{createdMatch.pot_amount} MON</strong></span>
                </div>
              </div>

              {/* Share & Copy Controls */}
              <div className="flex flex-wrap items-center gap-2">
                <ArcadeButton
                  variant="secondary"
                  size="sm"
                  onClick={() => spawnSimulatedOpponent(createdMatch.id)}
                  title="Spawn a local simulated duelist to playtest without a second browser window"
                >
                  <Bot className="w-3.5 h-3.5 mr-1.5 text-arcade-cyan" />
                  TEST WITH LOCAL BOT
                </ArcadeButton>

                <ArcadeButton
                  variant="secondary"
                  size="sm"
                  onClick={() => copyShareLink(createdMatch.id)}
                >
                  {isCopied ? (
                    <>
                      <Check className="w-3.5 h-3.5 mr-1.5 text-arcade-lime" />
                      COPIED LINK
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 mr-1.5" />
                      SHARE LINK
                    </>
                  )}
                </ArcadeButton>

                <ArcadeButton
                  variant="danger"
                  size="sm"
                  onClick={() => cancelDuel(createdMatch.id)}
                  title="Cancel lobby"
                >
                  <XCircle className="w-3.5 h-3.5 mr-1" />
                  CANCEL
                </ArcadeButton>
              </div>
            </div>

            {/* QR / Share Presentation Card */}
            <div className="p-4 rounded bg-arcade-panel-raised border border-arcade-border flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                {/* Visual QR presentation icon */}
                <div className="w-14 h-14 rounded bg-arcade-bg border border-arcade-pink/50 p-2 flex items-center justify-center text-arcade-pink shadow-arcade-pink/20">
                  <QrCode className="w-9 h-9" />
                </div>
                <div>
                  <div className="text-xs font-mono font-bold text-arcade-text">
                    SCAN OR TRANSMIT DUEL LINK
                  </div>
                  <div className="text-[11px] font-mono text-arcade-subtle mt-0.5">
                    Opponent can join via link or match ID #{createdMatch.id}
                  </div>
                </div>
              </div>

              <div className="text-center sm:text-right font-mono text-xs text-arcade-subtle">
                <span className="inline-block w-2 h-2 rounded-full bg-arcade-pink animate-ping mr-2" />
                <span>LISTENING ON MONAD LOBBY...</span>
              </div>
            </div>
          </div>
        </Panel>
      )}

      {/* Opponent Joined Notification & Arena Entrance */}
      {createdMatch && createdMatch.status !== 'WAITING' && (
        <div className="p-4 sm:p-5 rounded bg-arcade-lime/10 border border-arcade-lime/60 shadow-arcade-lime flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in fade-in">
          <div>
            <div className="font-display text-sm text-arcade-lime tracking-wider uppercase">
              OPPONENT ENTERED DUEL!
            </div>
            <p className="font-mono text-xs text-arcade-text mt-1">
              Opponent {createdMatch.opponent?.player_id ? `${createdMatch.opponent.player_id.slice(0, 8)}...` : 'Challenger'} locked their commitment. Duel is READY.
            </p>
          </div>
          <ArcadeButton
            variant="primary"
            size="md"
            className="w-full sm:w-auto shrink-0"
            onClick={() => navigate(`/bluff/${createdMatch.id}`)}
          >
            ENTER ARENA <ArrowRight className="w-4 h-4 ml-1.5" />
          </ArcadeButton>
        </div>
      )}

      {/* 4. Active Duel Stations (Server-Provided Lobbies) */}
      <Panel
        header={
          <div className="flex items-center justify-between w-full">
            <span className="font-display text-xs text-arcade-text tracking-wider">
              ACTIVE DUEL STATIONS ({openLobbies.length})
            </span>
            <button
              onClick={refreshLobbies}
              className="text-arcade-muted hover:text-arcade-pink transition-colors p-1 rounded focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-pink"
              aria-label="Refresh open duels"
              title="Refresh open duels list"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        }
        accent="pink"
      >
        {status === 'CONNECTING...' && openLobbies.length === 0 ? (
          <LoadingState status="CONNECTING" message="CONNECTING TO DUEL LOBBIES..." />
        ) : openLobbies.length === 0 ? (
          <div className="text-center py-10 space-y-3 font-mono">
            <Swords className="w-8 h-8 text-arcade-subtle mx-auto opacity-50" />
            <div className="text-xs text-arcade-muted font-bold tracking-wider uppercase">
              NO OPEN DUELS WAITING IN LOBBY
            </div>
            <p className="text-[11px] text-arcade-subtle max-w-sm mx-auto">
              Create a duel station above to initiate a match, or have a friend launch one on their device.
            </p>
            <ArcadeButton
              variant="secondary"
              size="sm"
              onClick={() => setIsCreateModalOpen(true)}
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              CREATE FIRST DUEL
            </ArcadeButton>
          </div>
        ) : (
          <div className="space-y-3">
            {openLobbies.map((lobby) => {
              const isOwnMatch = lobby.creator.player_id === playerId;

              return (
                <div
                  key={lobby.id}
                  className={`p-4 rounded bg-arcade-bg border ${
                    isOwnMatch ? 'border-arcade-pink/60 bg-arcade-pink/5' : 'border-arcade-border'
                  } flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded bg-arcade-panel border border-arcade-border flex items-center justify-center text-arcade-pink">
                      <Swords className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-mono text-xs font-bold text-arcade-text flex items-center gap-2">
                        <span>DUEL #{lobby.id}</span>
                        {isOwnMatch && (
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-arcade-pink/20 text-arcade-pink border border-arcade-pink/40">
                            YOUR LOBBY
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] font-mono text-arcade-subtle mt-0.5">
                        HOST: {lobby.creator?.player_id ? `${lobby.creator.player_id.slice(0, 8)}...` : 'HOST'} &bull; STAKE:{' '}
                        <strong className="text-arcade-text">{lobby.stake_amount} MON</strong> &bull; POT:{' '}
                        <strong className="text-arcade-pink">{lobby.pot_amount} MON</strong>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto justify-end pt-2 sm:pt-0 border-t sm:border-t-0 border-arcade-border/40">
                    {isOwnMatch ? (
                      <ArcadeButton
                        variant="secondary"
                        size="sm"
                        className="w-full sm:w-auto"
                        onClick={() => navigate(`/bluff/${lobby.id}`)}
                      >
                        VIEW STATION <ArrowRight className="w-3.5 h-3.5 ml-1" />
                      </ArcadeButton>
                    ) : (
                      <ArcadeButton
                        variant="pink"
                        size="sm"
                        className="w-full sm:w-auto"
                        onClick={() => {
                          setJoiningMatchId(lobby.id);
                        }}
                      >
                        JOIN DUEL <ArrowRight className="w-3.5 h-3.5 ml-1" />
                      </ArcadeButton>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      {/* 5. Sponsor Badge Component */}
      <SponsorBadge
        name={sponsor.name}
        tagline={sponsor.tagline}
        url={sponsor.url}
        onVisit={recordClick}
      />

      {/* ==================================================================== */}
      {/* Modal: CREATE DUEL */}
      {/* ==================================================================== */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="HOST 1v1 BLUFF DUEL"
        maxWidth="md"
        footer={
          <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2 sm:gap-3 w-full">
            <ArcadeButton
              variant="secondary"
              size="sm"
              className="w-full sm:w-auto"
              onClick={() => setIsCreateModalOpen(false)}
              disabled={isCreating}
            >
              CANCEL
            </ArcadeButton>
            <ArcadeButton
              variant="pink"
              size="md"
              className="w-full sm:w-auto"
              onClick={handleCreateSubmit}
              isLoading={isCreating}
            >
              LOCK COMMITMENT & HOST
            </ArcadeButton>
          </div>
        }
      >
        <div className="space-y-5 font-mono">
          {/* Stake Amount Selector */}
          <div>
            <label className="block text-xs font-bold text-arcade-muted mb-2 uppercase">
              1. SELECT STAKE AMOUNT (MON)
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[1, 5, 10, 25].map((amount) => (
                <button
                  key={amount}
                  type="button"
                  onClick={() => setSelectedStake(amount)}
                  aria-label={`Select stake of ${amount} MON`}
                  className={`py-2.5 px-3 rounded text-center text-xs font-bold transition-all border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-pink ${
                    selectedStake === amount
                      ? 'bg-arcade-pink text-white border-arcade-pink shadow-arcade-pink'
                      : 'bg-arcade-bg text-arcade-muted border-arcade-border hover:border-arcade-pink/50'
                  }`}
                >
                  {amount} MON
                </button>
              ))}
            </div>
            <p className="text-[11px] text-arcade-subtle mt-1.5">
              Pot size will be <strong className="text-arcade-text">{selectedStake * 2} MON</strong> (winner takes all).
            </p>
          </div>

          {/* Secret Card Number Selector */}
          <div>
            <label className="block text-xs font-bold text-arcade-muted mb-2 uppercase">
              2. CHOOSE YOUR HIDDEN SECRET NUMBER (1 - 10)
            </label>
            <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => setSelectedSecret(num)}
                  aria-label={`Select secret card value ${num}`}
                  className={`h-11 rounded text-center font-display text-base transition-all border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-pink ${
                    selectedSecret === num
                      ? 'bg-arcade-pink text-white border-arcade-pink shadow-arcade-pink scale-105 motion-reduce:transform-none'
                      : 'bg-arcade-bg text-arcade-text border-arcade-border hover:border-arcade-pink/50'
                  }`}
                >
                  {num}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-2 text-[11px] text-arcade-subtle">
              <EyeOff className="w-3.5 h-3.5 text-arcade-pink" />
              <span>Cryptographically salted & hashed with SHA-256 before lobby entry.</span>
            </div>
          </div>
        </div>
      </Modal>

      {/* ==================================================================== */}
      {/* Modal: JOIN DUEL */}
      {/* ==================================================================== */}
      <Modal
        isOpen={Boolean(joiningMatchId)}
        onClose={() => setJoiningMatchId(null)}
        title={`ENTER DUEL #${joiningMatchId || ''}`}
        maxWidth="md"
        footer={
          <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2 sm:gap-3 w-full">
            <ArcadeButton
              variant="secondary"
              size="sm"
              className="w-full sm:w-auto"
              onClick={() => setJoiningMatchId(null)}
              disabled={isJoining}
            >
              CANCEL
            </ArcadeButton>
            <ArcadeButton
              variant="pink"
              size="md"
              className="w-full sm:w-auto"
              onClick={handleJoinSubmit}
              isLoading={isJoining}
            >
              CONFIRM & ENTER ARENA
            </ArcadeButton>
          </div>
        }
      >
        <div className="space-y-5 font-mono">
          <p className="text-xs font-sans text-arcade-muted">
            You are challenging match <strong className="text-arcade-text">#{joiningMatchId}</strong>.
            Choose your secret card value to lock your commitment.
          </p>

          {/* Secret Card Number Selector */}
          <div>
            <label className="block text-xs font-bold text-arcade-muted mb-2 uppercase">
              CHOOSE YOUR SECRET NUMBER (1 - 10)
            </label>
            <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => setJoinSecret(num)}
                  aria-label={`Select secret card value ${num}`}
                  className={`h-11 rounded text-center font-display text-base transition-all border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-pink ${
                    joinSecret === num
                      ? 'bg-arcade-pink text-white border-arcade-pink shadow-arcade-pink scale-105 motion-reduce:transform-none'
                      : 'bg-arcade-bg text-arcade-text border-arcade-border hover:border-arcade-pink/50'
                  }`}
                >
                  {num}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-2 text-[11px] text-arcade-subtle">
              <EyeOff className="w-3.5 h-3.5 text-arcade-pink" />
              <span>Your choice remains hidden from the opponent until showdown reveal.</span>
            </div>
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
};
