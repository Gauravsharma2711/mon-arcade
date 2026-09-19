import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/PageContainer';
import { Panel } from '../components/Panel';
import { ArcadeButton } from '../components/ArcadeButton';
import { SponsorBadge } from '../components/SponsorBadge';
import { TransactionState, TxStatus } from '../components/TransactionState';
import { Toast, ToastMessage } from '../components/Toast';
import {
  ArrowLeft,
  ArrowRight,
  Shield,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import {
  sponsorApi,
  CampaignDetailData,
  FundingInitiationData,
} from '../lib/sponsorApi';
import { PlacementSlot } from './types';

export const SponsorCreatePage: React.FC = () => {
  const navigate = useNavigate();

  // Wizard Stage: 'CONFIG' (Brand + Placement + Budget) | 'FUNDING' (Escrow deposit) | 'COMPLETE'
  const [stage, setStage] = useState<'CONFIG' | 'FUNDING' | 'COMPLETE'>('CONFIG');

  // Form inputs
  const [brandName, setBrandName] = useState<string>('');
  const [tagline, setTagline] = useState<string>('');
  const [destinationUrl, setDestinationUrl] = useState<string>('');
  const [walletAddress, setWalletAddress] = useState<string>('');
  const [logoUrl, setLogoUrl] = useState<string>('');
  const [selectedSlot, setSelectedSlot] = useState<PlacementSlot>('HOME_MARQUEE');
  const [budget, setBudget] = useState<number>(50);
  const [durationDays, setDurationDays] = useState<number>(14);
  const [autoActivate, setAutoActivate] = useState<boolean>(true);

  // Validation
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Asynchronous & Funding State
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [createdCampaign, setCreatedCampaign] = useState<CampaignDetailData | null>(null);
  const [fundingData, setFundingData] = useState<FundingInitiationData | null>(null);
  const [txStatus, setTxStatus] = useState<TxStatus>('IDLE');
  const [txHash, setTxHash] = useState<string | undefined>(undefined);
  const [txErrorMessage, setTxErrorMessage] = useState<string | undefined>(undefined);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (type: ToastMessage['type'], title: string, message?: string) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Helper for quick test wallet
  const handleUseMockWallet = () => {
    setWalletAddress('0x71C63397e68221f70cf07999018A509d3307C4aa');
    if (errors.walletAddress) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next.walletAddress;
        return next;
      });
    }
  };

  // Helper for demo brand
  const handleFillDemoBrand = () => {
    setBrandName('Monad Foundation');
    setTagline('High-throughput 10,000 TPS parallel EVM execution');
    setDestinationUrl('https://monad.xyz');
    setWalletAddress('0x71C63397e68221f70cf07999018A509d3307C4aa');
    setErrors({});
  };

  // Validate Step 1
  const validateForm = (): boolean => {
    const nextErrors: Record<string, string> = {};

    if (!brandName.trim()) {
      nextErrors.brandName = 'Brand / Sponsor name is required';
    } else if (brandName.trim().length > 64) {
      nextErrors.brandName = 'Brand name must be under 64 characters';
    }

    if (!tagline.trim()) {
      nextErrors.tagline = 'Tagline is required';
    } else if (tagline.trim().length > 60) {
      nextErrors.tagline = 'Tagline must be at most 60 characters';
    }

    if (!destinationUrl.trim()) {
      nextErrors.destinationUrl = 'Destination URL is required';
    } else {
      try {
        const parsed = new URL(destinationUrl.trim());
        if (!['http:', 'https:'].includes(parsed.protocol)) {
          nextErrors.destinationUrl = 'URL must start with http:// or https://';
        }
      } catch {
        nextErrors.destinationUrl = 'Invalid URL format (e.g. https://monad.xyz)';
      }
    }

    const ethRegex = /^0x[a-fA-F0-9]{40}$/;
    if (!walletAddress.trim()) {
      nextErrors.walletAddress = 'Monad/EVM wallet address is required';
    } else if (!ethRegex.test(walletAddress.trim())) {
      nextErrors.walletAddress = 'Must be a valid 42-char EVM address (0x...)';
    }

    if (budget < 10) {
      nextErrors.budget = 'Minimum budget is 10 MON';
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  // Proceed from CONFIG to FUNDING stage
  const handleProceedToFunding = async () => {
    if (!validateForm()) {
      addToast('error', 'Validation Incomplete', 'Please correct the highlighted fields.');
      return;
    }

    setSubmitting(true);
    try {
      // 1. Register sponsor entity
      const sponsor = await sponsorApi.createSponsor({
        name: brandName.trim(),
        wallet: walletAddress.trim(),
        website: destinationUrl.trim(),
        logo: logoUrl.trim() || null,
      });

      addToast('success', 'Sponsor Entity Registered', `Brand ID: ${sponsor.sponsor_id}`);

      // 2. Create campaign in DRAFT
      const now = new Date();
      const end = new Date(now.getTime() + durationDays * 24 * 60 * 60 * 1000);

      const campaign = await sponsorApi.createCampaign({
        sponsor_id: sponsor.sponsor_id,
        placement: selectedSlot,
        budget: budget,
        start_at: now.toISOString(),
        end_at: end.toISOString(),
        auto_fund: false,
      });

      setCreatedCampaign(campaign);

      // 3. Initiate payment -> transitions to PAYMENT_PENDING
      const initiation = await sponsorApi.initiateFunding(campaign.id);
      setFundingData(initiation);
      setTxStatus('WAITING');
      setStage('FUNDING');

      addToast('info', 'Payment Escrow Initiated', 'Awaiting mock signature confirmation.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to initialize campaign';
      addToast('error', 'Initialization Error', msg);
    } finally {
      setSubmitting(false);
    }
  };

  // Confirm funding via MockBlockchain
  const handleConfirmFunding = async () => {
    if (!createdCampaign) return;

    setTxStatus('CONFIRMING');
    setTxErrorMessage(undefined);

    try {
      // Simulate network confirmation latency (500ms)
      await new Promise((r) => setTimeout(r, 600));

      const updated = await sponsorApi.confirmFunding(createdCampaign.id, {
        auto_activate: autoActivate,
      });

      setCreatedCampaign(updated);
      setTxStatus('SUCCESS');
      setTxHash(updated.vault?.deposit_tx || '0xmock_sponsor_confirmed');
      setStage('COMPLETE');

      addToast(
        'success',
        'Escrow Deposit Confirmed',
        autoActivate ? 'Campaign funded and placement is now ACTIVE.' : 'Campaign funded.'
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Confirmation failed';
      setTxStatus('FAILED');
      setTxErrorMessage(msg);
      addToast('error', 'Deposit Failed', msg);
    }
  };

  // Simulate payment rejection to verify failure & retry recovery
  const handleSimulateFailure = async () => {
    if (!createdCampaign) return;

    setTxStatus('CONFIRMING');
    setTxErrorMessage(undefined);

    try {
      await new Promise((r) => setTimeout(r, 400));
      const updated = await sponsorApi.failFunding(
        createdCampaign.id,
        'Simulated mock user rejection or insufficient test gas'
      );
      setCreatedCampaign(updated);
      setTxStatus('FAILED');
      setTxErrorMessage('Transaction rejected by user (Simulated Payment Failure).');
      addToast('warning', 'Payment Failed', 'Failure recorded. You can safely retry.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Fail simulation error';
      setTxStatus('FAILED');
      setTxErrorMessage(msg);
    }
  };

  // Recover from PAYMENT_FAILED back to PAYMENT_PENDING
  const handleRetryFunding = async () => {
    if (!createdCampaign) return;

    setTxStatus('LOADING');
    try {
      const initiation = await sponsorApi.initiateFunding(createdCampaign.id);
      setFundingData(initiation);
      setTxStatus('WAITING');
      setTxErrorMessage(undefined);
      addToast('info', 'Retry Initiated', 'Ready to sign deposit again.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Retry failed';
      setTxStatus('FAILED');
      setTxErrorMessage(msg);
    }
  };

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* Toast notifications */}
      <Toast toasts={toasts} onDismiss={dismissToast} />

      {/* Header & Flow Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-arcade-border gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/sponsor"
            className="text-arcade-muted hover:text-arcade-text p-1.5 rounded border border-arcade-border hover:border-arcade-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcade-lime transition-colors"
            aria-label="Back to Sponsor Portal"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="font-display text-xl text-arcade-lime tracking-wider flex items-center gap-2">
              <span>CREATE SPONSOR CAMPAIGN</span>
              <span className="text-[10px] font-mono border border-arcade-lime/30 text-arcade-lime/80 px-1.5 py-0.2 rounded uppercase">
                BETA
              </span>
            </h1>
            <p className="text-xs font-mono text-arcade-muted mt-0.5">
              RESERVE HIGH-ATTENTION SUBORDINATE PLACEMENT ON MONAD
            </p>
          </div>
        </div>

        {/* Quick Demo Pre-Fill button */}
        {stage === 'CONFIG' && (
          <ArcadeButton
            variant="secondary"
            size="sm"
            onClick={handleFillDemoBrand}
            title="Pre-fill standard demo values"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1 text-arcade-lime" />
            FILL DEMO VALUES
          </ArcadeButton>
        )}
      </div>

      {/* Step Indicator */}
      <div className="grid grid-cols-3 gap-2 font-mono text-xs">
        <div
          className={`p-2.5 rounded border transition-colors ${
            stage === 'CONFIG'
              ? 'bg-arcade-panel border-arcade-lime text-arcade-lime shadow-arcade-lime'
              : 'bg-arcade-bg/40 border-arcade-border text-arcade-subtle'
          }`}
        >
          <div className="text-[10px] text-arcade-subtle">STEP 1</div>
          <div className="font-semibold truncate">1. BRAND &amp; PLACEMENT</div>
        </div>

        <div
          className={`p-2.5 rounded border transition-colors ${
            stage === 'FUNDING'
              ? 'bg-arcade-panel border-arcade-warning text-arcade-warning'
              : 'bg-arcade-bg/40 border-arcade-border text-arcade-subtle'
          }`}
        >
          <div className="text-[10px] text-arcade-subtle">STEP 2</div>
          <div className="font-semibold truncate">2. LOCK ESCROW</div>
        </div>

        <div
          className={`p-2.5 rounded border transition-colors ${
            stage === 'COMPLETE'
              ? 'bg-arcade-panel border-arcade-lime text-arcade-lime shadow-arcade-lime'
              : 'bg-arcade-bg/40 border-arcade-border text-arcade-subtle'
          }`}
        >
          <div className="text-[10px] text-arcade-subtle">STEP 3</div>
          <div className="font-semibold truncate">3. STATUS &amp; LIVE</div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* STAGE 1: CONFIGURATION (Brand Details + Placement Slot + Live Preview + Budget) */}
      {/* ========================================================================= */}
      {stage === 'CONFIG' && (
        <div className="space-y-6">
          {/* Brand Identity Form */}
          <Panel header="1. BRAND & IDENTITY">
            <div className="space-y-4 font-mono text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Brand Name */}
                <div>
                  <label className="block text-arcade-subtle uppercase mb-1">
                    BRAND / SPONSOR NAME <span className="text-arcade-danger">*</span>
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={(e) => {
                      setBrandName(e.target.value);
                      if (errors.brandName) setErrors((p) => ({ ...p, brandName: '' }));
                    }}
                    placeholder="e.g. Monad Ecosystem Fund"
                    maxLength={64}
                    className={`w-full px-3 py-2 rounded bg-arcade-bg border text-arcade-text focus:outline-none transition-colors ${
                      errors.brandName
                        ? 'border-arcade-danger focus:border-arcade-danger'
                        : 'border-arcade-border focus:border-arcade-lime'
                    }`}
                  />
                  {errors.brandName && (
                    <p className="text-[11px] text-arcade-danger mt-1">{errors.brandName}</p>
                  )}
                </div>

                {/* Destination URL */}
                <div>
                  <label className="block text-arcade-subtle uppercase mb-1">
                    DESTINATION WEBSITE URL <span className="text-arcade-danger">*</span>
                  </label>
                  <input
                    type="url"
                    value={destinationUrl}
                    onChange={(e) => {
                      setDestinationUrl(e.target.value);
                      if (errors.destinationUrl) setErrors((p) => ({ ...p, destinationUrl: '' }));
                    }}
                    placeholder="https://monad.xyz"
                    className={`w-full px-3 py-2 rounded bg-arcade-bg border text-arcade-text focus:outline-none transition-colors ${
                      errors.destinationUrl
                        ? 'border-arcade-danger focus:border-arcade-danger'
                        : 'border-arcade-border focus:border-arcade-lime'
                    }`}
                  />
                  {errors.destinationUrl && (
                    <p className="text-[11px] text-arcade-danger mt-1">{errors.destinationUrl}</p>
                  )}
                </div>
              </div>

              {/* Tagline */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-arcade-subtle uppercase">
                    TAGLINE (MAX 60 CHARACTERS) <span className="text-arcade-danger">*</span>
                  </label>
                  <span className={`text-[11px] ${tagline.length > 55 ? 'text-arcade-warning' : 'text-arcade-subtle'}`}>
                    {tagline.length}/60
                  </span>
                </div>
                <input
                  type="text"
                  value={tagline}
                  maxLength={60}
                  onChange={(e) => {
                    setTagline(e.target.value);
                    if (errors.tagline) setErrors((p) => ({ ...p, tagline: '' }));
                  }}
                  placeholder="e.g. Scaling Ethereum execution at 10,000 TPS"
                  className={`w-full px-3 py-2 rounded bg-arcade-bg border text-arcade-text focus:outline-none transition-colors ${
                    errors.tagline
                      ? 'border-arcade-danger focus:border-arcade-danger'
                      : 'border-arcade-border focus:border-arcade-lime'
                  }`}
                />
                {errors.tagline && (
                  <p className="text-[11px] text-arcade-danger mt-1">{errors.tagline}</p>
                )}
              </div>

              {/* Wallet Address */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-arcade-subtle uppercase">
                    MONAD / EVM WALLET ADDRESS <span className="text-arcade-danger">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={handleUseMockWallet}
                    className="text-[10px] text-arcade-lime hover:underline tracking-wider"
                  >
                    [USE LOCAL TEST WALLET]
                  </button>
                </div>
                <input
                  type="text"
                  value={walletAddress}
                  onChange={(e) => {
                    setWalletAddress(e.target.value.trim());
                    if (errors.walletAddress) setErrors((p) => ({ ...p, walletAddress: '' }));
                  }}
                  placeholder="0x..."
                  className={`w-full px-3 py-2 rounded bg-arcade-bg border text-arcade-text font-mono focus:outline-none transition-colors ${
                    errors.walletAddress
                      ? 'border-arcade-danger focus:border-arcade-danger'
                      : 'border-arcade-border focus:border-arcade-lime'
                  }`}
                />
                {errors.walletAddress && (
                  <p className="text-[11px] text-arcade-danger mt-1">{errors.walletAddress}</p>
                )}
              </div>

              {/* Optional Logo */}
              <div>
                <label className="block text-arcade-subtle uppercase mb-1">
                  BRAND LOGO URL <span className="text-arcade-muted font-normal">(OPTIONAL)</span>
                </label>
                <input
                  type="url"
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="https://example.com/logo.png"
                  className="w-full px-3 py-2 rounded bg-arcade-bg border border-arcade-border text-arcade-text focus:outline-none focus:border-arcade-lime"
                />
              </div>
            </div>
          </Panel>

          {/* Placement Selection & Live Subordinate Preview */}
          <Panel header="2. SELECT PLACEMENT & REAL-TIME PREVIEW">
            <div className="space-y-4">
              <div className="text-xs text-arcade-muted leading-relaxed font-sans">
                Choose the screen location to reserve. In accordance with the Mon Arcade design system:
                <div className="p-2 mt-2 rounded bg-arcade-bg border border-arcade-border text-[11px] font-mono text-arcade-subtle">
                  HIERARCHY: <span className="text-arcade-lime">Game &gt; Game Action &gt; Game State &gt; Sponsor</span>
                  <p className="mt-0.5 text-arcade-muted font-sans">
                    Sponsors are strictly subordinate to gameplay, never block interactive controls, and never alter game rules.
                  </p>
                </div>
              </div>

              {/* Placement Slot Selector */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
                <button
                  type="button"
                  onClick={() => setSelectedSlot('HOME_MARQUEE')}
                  className={`p-3 rounded border text-left transition-all ${
                    selectedSlot === 'HOME_MARQUEE'
                      ? 'border-arcade-lime bg-arcade-lime/10 text-arcade-lime'
                      : 'border-arcade-border bg-arcade-bg text-arcade-muted hover:text-arcade-text hover:border-arcade-subtle'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold">HOME MARQUEE</span>
                    {selectedSlot === 'HOME_MARQUEE' && <CheckCircle2 className="w-3.5 h-3.5" />}
                  </div>
                  <p className="text-[11px] text-arcade-subtle leading-tight font-sans">
                    Arcade home lobby. High discovery marquee below game cabinets.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedSlot('BLUFF_LOBBY')}
                  className={`p-3 rounded border text-left transition-all ${
                    selectedSlot === 'BLUFF_LOBBY'
                      ? 'border-arcade-pink bg-arcade-pink/10 text-arcade-pink'
                      : 'border-arcade-border bg-arcade-bg text-arcade-muted hover:text-arcade-text hover:border-arcade-subtle'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold">BLUFF LOBBY</span>
                    {selectedSlot === 'BLUFF_LOBBY' && <CheckCircle2 className="w-3.5 h-3.5" />}
                  </div>
                  <p className="text-[11px] text-arcade-subtle leading-tight font-sans">
                    PvP duel room. Secondary badge beside wager setup panel.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedSlot('VAULT_SETUP')}
                  className={`p-3 rounded border text-left transition-all ${
                    selectedSlot === 'VAULT_SETUP'
                      ? 'border-arcade-cyan bg-arcade-cyan/10 text-arcade-cyan'
                      : 'border-arcade-border bg-arcade-bg text-arcade-muted hover:text-arcade-text hover:border-arcade-subtle'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold">VAULT LOADOUT</span>
                    {selectedSlot === 'VAULT_SETUP' && <CheckCircle2 className="w-3.5 h-3.5" />}
                  </div>
                  <p className="text-[11px] text-arcade-subtle leading-tight font-sans">
                    AI battle preparation. Secondary badge below stat allocation.
                  </p>
                </button>
              </div>

              {/* Real-time Subordinate Badge Preview */}
              <div className="pt-2">
                <div className="flex items-center justify-between text-[11px] font-mono text-arcade-subtle mb-1.5 uppercase">
                  <span className="flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-arcade-lime" />
                    LIVE SUBORDINATE BADGE PREVIEW
                  </span>
                  <span>SLOT: {selectedSlot}</span>
                </div>
                <div className="p-3.5 rounded bg-arcade-bg border border-arcade-border/80">
                  <SponsorBadge
                    name={brandName.trim() || 'YOUR BRAND NAME'}
                    tagline={tagline.trim() || 'YOUR PROJECT VALUE PROPOSITION GOES HERE'}
                    url={destinationUrl.trim() || 'https://monad.xyz'}
                  />
                </div>
              </div>
            </div>
          </Panel>

          {/* Campaign Budget & Terms */}
          <Panel header="3. BUDGET & CAMPAIGN TERMS">
            <div className="space-y-4 font-mono text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Budget input with quick presets */}
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="block text-arcade-subtle uppercase">
                      ESCROW BUDGET (MON) <span className="text-arcade-danger">*</span>
                    </label>
                    <div className="flex gap-1">
                      {[25, 50, 100].map((val) => (
                        <button
                          key={val}
                          type="button"
                          onClick={() => setBudget(val)}
                          className={`px-1.5 py-0.5 rounded text-[10px] border ${
                            budget === val
                              ? 'border-arcade-lime text-arcade-lime bg-arcade-lime/10'
                              : 'border-arcade-border text-arcade-subtle hover:text-arcade-text'
                          }`}
                        >
                          {val} MON
                        </button>
                      ))}
                    </div>
                  </div>
                  <input
                    type="number"
                    min={10}
                    step={5}
                    value={budget}
                    onChange={(e) => setBudget(Math.max(10, Number(e.target.value)))}
                    className="w-full px-3 py-2 rounded bg-arcade-bg border border-arcade-border text-arcade-text font-bold text-sm focus:outline-none focus:border-arcade-lime"
                  />
                  {errors.budget && (
                    <p className="text-[11px] text-arcade-danger mt-1">{errors.budget}</p>
                  )}
                </div>

                {/* Duration */}
                <div>
                  <label className="block text-arcade-subtle uppercase mb-1">
                    CAMPAIGN DURATION
                  </label>
                  <select
                    value={durationDays}
                    onChange={(e) => setDurationDays(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-arcade-bg border border-arcade-border text-arcade-text focus:outline-none focus:border-arcade-lime"
                  >
                    <option value={7}>7 Days (Active Window)</option>
                    <option value={14}>14 Days (Standard Window)</option>
                    <option value={30}>30 Days (Extended Window)</option>
                  </select>
                </div>
              </div>

              {/* Auto activate toggle */}
              <div className="pt-2 flex items-center justify-between p-3 rounded bg-arcade-bg border border-arcade-border">
                <div className="space-y-0.5">
                  <div className="font-semibold text-arcade-text">
                    AUTO-ACTIVATE PLACEMENT
                  </div>
                  <p className="text-[11px] text-arcade-subtle font-sans">
                    Automatically activate the placement slot once mock escrow deposit is confirmed.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={autoActivate}
                  onChange={(e) => setAutoActivate(e.target.checked)}
                  className="w-4 h-4 accent-arcade-lime cursor-pointer rounded focus-visible:ring-2 focus-visible:ring-arcade-lime"
                />
              </div>

              {/* Proceed Button */}
              <div className="pt-2">
                <ArcadeButton
                  variant="primary"
                  size="md"
                  className="w-full justify-center"
                  onClick={handleProceedToFunding}
                  isLoading={submitting}
                  disabled={submitting}
                >
                  <span>INITIALIZE ESCROW &amp; PROCEED TO FUNDING</span>
                  <ArrowRight className="w-4 h-4 ml-1.5" />
                </ArcadeButton>
              </div>
            </div>
          </Panel>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STAGE 2: FUNDING (Mock Blockchain Deposit & Verification) */}
      {/* ========================================================================= */}
      {stage === 'FUNDING' && createdCampaign && fundingData && (
        <div className="space-y-6">
          <Panel header="LOCK ESCROW ON MONAD (MOCK SETTLEMENT)">
            <div className="space-y-5 font-mono text-xs">
              {/* Campaign summary strip */}
              <div className="p-3.5 rounded bg-arcade-bg border border-arcade-border space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-arcade-border/60 pb-2">
                  <span className="font-bold text-arcade-text tracking-wide">
                    CAMPAIGN #{createdCampaign.id}
                  </span>
                  <span className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded border border-arcade-warning/40 text-arcade-warning bg-arcade-warning/10">
                    PAYMENT_PENDING
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                  <div>
                    <span className="text-arcade-subtle block">SPONSOR</span>
                    <span className="text-arcade-text font-semibold truncate block">
                      {brandName}
                    </span>
                  </div>
                  <div>
                    <span className="text-arcade-subtle block">SLOT</span>
                    <span className="text-arcade-text font-semibold block">
                      {selectedSlot}
                    </span>
                  </div>
                  <div>
                    <span className="text-arcade-subtle block">ESCROW AMOUNT</span>
                    <span className="text-arcade-lime font-bold block">
                      {budget} MON
                    </span>
                  </div>
                  <div>
                    <span className="text-arcade-subtle block">ENVIRONMENT</span>
                    <span className="text-arcade-cyan block truncate">
                      monad-mock-local
                    </span>
                  </div>
                </div>
              </div>

              {/* Escrow recipient disclosure */}
              <div className="p-3 rounded bg-arcade-panel border border-arcade-border/70 space-y-1.5">
                <div className="flex items-center gap-1.5 text-arcade-subtle text-[11px]">
                  <Shield className="w-3.5 h-3.5 text-arcade-lime" />
                  <span>MOCK ESCROW VAULT RECIPIENT</span>
                </div>
                <div className="font-mono text-arcade-muted select-all break-all bg-arcade-bg p-2 rounded border border-arcade-border/50 text-[11px]">
                  {fundingData.deposit_recipient}
                </div>
                <p className="text-[11px] font-sans text-arcade-subtle leading-relaxed">
                  Notice: Mon Arcade runs against a deterministic local mock blockchain adapter. No real mainnet funds are transacted. Escrow records are persisted locally.
                </p>
              </div>

              {/* Transaction State Banner */}
              <TransactionState
                status={txStatus}
                txHash={txHash}
                errorMessage={txErrorMessage}
                onRetry={handleRetryFunding}
              />

              {/* Funding Actions */}
              <div className="space-y-2 pt-2">
                {txStatus !== 'FAILED' && (
                  <ArcadeButton
                    variant="primary"
                    size="md"
                    className="w-full justify-center"
                    onClick={handleConfirmFunding}
                    disabled={txStatus === 'CONFIRMING' || txStatus === 'LOADING'}
                    isLoading={txStatus === 'CONFIRMING'}
                  >
                    <span>SIGN &amp; DEPOSIT {budget} MON [MOCK BLOCKCHAIN]</span>
                    <CheckCircle2 className="w-4 h-4 ml-1.5" />
                  </ArcadeButton>
                )}

                {/* Secondary / Failure Recovery Simulation button */}
                {txStatus !== 'FAILED' && txStatus !== 'CONFIRMING' && (
                  <div className="pt-2 border-t border-arcade-border/40">
                    <ArcadeButton
                      variant="danger"
                      size="sm"
                      className="w-full justify-center"
                      onClick={handleSimulateFailure}
                    >
                      <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                      SIMULATE PAYMENT REJECTION (TEST FAILURE &amp; RETRY)
                    </ArcadeButton>
                    <p className="text-[10px] text-arcade-subtle text-center mt-1">
                      Tests payment state machine transition: PAYMENT_PENDING &rarr; PAYMENT_FAILED &rarr; RETRY
                    </p>
                  </div>
                )}
              </div>
            </div>
          </Panel>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STAGE 3: COMPLETE (Campaign Activated / Ready for Management) */}
      {/* ========================================================================= */}
      {stage === 'COMPLETE' && createdCampaign && (
        <div className="space-y-6">
          <Panel header="ESCROW CONFIRMED &amp; CAMPAIGN INITIALIZED">
            <div className="text-center py-6 space-y-4 font-mono">
              <div className="w-12 h-12 rounded-full border border-arcade-lime/50 bg-arcade-lime/10 flex items-center justify-center mx-auto text-arcade-lime">
                <CheckCircle2 className="w-6 h-6" />
              </div>

              <div>
                <h2 className="text-base font-bold text-arcade-text tracking-wider">
                  CAMPAIGN #{createdCampaign.id} ACTIVE
                </h2>
                <p className="text-xs text-arcade-muted mt-1 font-sans max-w-md mx-auto">
                  Your placement escrow has been successfully recorded on the local MockBlockchain ledger. Attention metrics are now ready to stream.
                </p>
              </div>

              {/* Settlement disclosure badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-arcade-panel border border-arcade-lime/30 text-[11px] text-arcade-lime">
                <span className="w-2 h-2 rounded-full bg-arcade-lime animate-pulse" />
                <span>[MOCK / LOCAL SETTLEMENT CONFIRMED]</span>
                <span className="text-arcade-muted font-mono">{txHash}</span>
              </div>

              {/* Live rendered badge preview */}
              <div className="max-w-md mx-auto p-3 rounded bg-arcade-bg border border-arcade-border text-left">
                <div className="text-[10px] text-arcade-subtle mb-1.5 uppercase flex items-center justify-between">
                  <span>ACTIVE ON: {selectedSlot}</span>
                  <span className="text-arcade-lime font-bold">LIVE</span>
                </div>
                <SponsorBadge
                  name={brandName}
                  tagline={tagline}
                  url={destinationUrl}
                />
              </div>

              {/* Navigation CTAs */}
              <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3 w-full">
                <ArcadeButton
                  variant="primary"
                  size="md"
                  className="w-full sm:w-auto"
                  onClick={() => navigate(`/sponsor/${createdCampaign.id}`)}
                >
                  <span>VIEW CAMPAIGN STATUS &amp; TELEMETRY</span>
                  <ArrowRight className="w-4 h-4 ml-1.5" />
                </ArcadeButton>

                <Link to="/sponsor" className="w-full sm:w-auto">
                  <ArcadeButton variant="secondary" size="md" className="w-full sm:w-auto">
                    <span>BACK TO SPONSOR PORTAL</span>
                  </ArcadeButton>
                </Link>
              </div>
            </div>
          </Panel>
        </div>
      )}
    </PageContainer>
  );
};
