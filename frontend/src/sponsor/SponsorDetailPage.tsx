import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PageContainer } from '../components/PageContainer';
import { Panel } from '../components/Panel';
import { ArcadeButton } from '../components/ArcadeButton';
import { SponsorBadge } from '../components/SponsorBadge';
import { LoadingState } from '../components/LoadingState';
import { TransactionState, TxStatus } from '../components/TransactionState';
import { Toast, ToastMessage } from '../components/Toast';
import {
  ArrowLeft,
  ExternalLink,
  Shield,
  Eye,
  MousePointerClick,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import {
  sponsorApi,
  CampaignDetailData,
} from '../lib/sponsorApi';
import { Sponsor } from './types';

export const SponsorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  // State
  const [campaign, setCampaign] = useState<CampaignDetailData | null>(null);
  const [sponsor, setSponsor] = useState<Sponsor | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Action / Transaction State
  const [txStatus, setTxStatus] = useState<TxStatus>('IDLE');
  const [txHash, setTxHash] = useState<string | undefined>(undefined);
  const [txErrorMessage, setTxErrorMessage] = useState<string | undefined>(undefined);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((type: ToastMessage['type'], title: string, message?: string) => {
    const toastId = `toast_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    setToasts((prev) => [...prev, { id: toastId, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== toastId));
    }, 4500);
  }, []);

  const dismissToast = useCallback((toastId: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId));
  }, []);

  // Fetch campaign and sponsor
  const loadCampaignData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const cmp = await sponsorApi.getCampaign(id);
      setCampaign(cmp);
      if (cmp.vault?.deposit_tx) {
        setTxHash(cmp.vault.deposit_tx);
      }

      // Fetch sponsor brand entity
      if (cmp.sponsor_id) {
        try {
          const sp = await sponsorApi.getSponsor(cmp.sponsor_id);
          setSponsor(sp);
        } catch {
          // Sponsor info fallback
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not fetch campaign details';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadCampaignData();
  }, [loadCampaignData]);

  // Initiate Funding (DRAFT or PAYMENT_FAILED -> PAYMENT_PENDING)
  const handleInitiateFunding = async () => {
    if (!campaign) return;
    setActionLoading(true);
    setTxStatus('LOADING');
    try {
      await sponsorApi.initiateFunding(campaign.id);
      addToast('info', 'Funding Initiated', 'Campaign transitioned to PAYMENT_PENDING.');
      await loadCampaignData();
      setTxStatus('WAITING');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not initiate funding';
      setTxStatus('FAILED');
      setTxErrorMessage(msg);
      addToast('error', 'Initiation Failed', msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Confirm Funding (PAYMENT_PENDING -> FUNDED)
  const handleConfirmFunding = async () => {
    if (!campaign) return;
    setActionLoading(true);
    setTxStatus('CONFIRMING');
    setTxErrorMessage(undefined);
    try {
      // Simulate mock delay
      await new Promise((r) => setTimeout(r, 600));
      const updated = await sponsorApi.confirmFunding(campaign.id, { auto_activate: false });
      setCampaign(updated);
      setTxHash(updated.vault?.deposit_tx || undefined);
      setTxStatus('SUCCESS');
      addToast('success', 'Escrow Locked', 'Mock blockchain funding confirmed.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to confirm funding';
      setTxStatus('FAILED');
      setTxErrorMessage(msg);
      addToast('error', 'Confirmation Failed', msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Fail Funding (Simulate failure transition)
  const handleSimulateFailure = async () => {
    if (!campaign) return;
    setActionLoading(true);
    setTxStatus('CONFIRMING');
    try {
      await new Promise((r) => setTimeout(r, 400));
      const updated = await sponsorApi.failFunding(campaign.id, 'User test failure simulation');
      setCampaign(updated);
      setTxStatus('FAILED');
      setTxErrorMessage('Deposit transaction rejected (Simulated test failure).');
      addToast('warning', 'Payment Failed', 'State transitioned to PAYMENT_FAILED. Retry available.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to trigger failure simulation';
      setTxStatus('FAILED');
      setTxErrorMessage(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Activate Campaign (FUNDED -> ACTIVE)
  const handleActivateCampaign = async () => {
    if (!campaign) return;
    setActionLoading(true);
    try {
      const updated = await sponsorApi.activateCampaign(campaign.id);
      setCampaign(updated);
      addToast('success', 'Campaign Activated', 'Placement is now live across Mon Arcade.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Activation failed';
      addToast('error', 'Activation Failed', msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Telemetry: Simulate Impression
  const handleSimulateImpression = async () => {
    if (!campaign) return;
    const placementId = `pl_${campaign.id}`;
    try {
      await sponsorApi.recordImpression(placementId);
      addToast('info', 'Impression Recorded', 'Logged display telemetry event.');
      // Refresh analytics
      const updated = await sponsorApi.getCampaign(campaign.id);
      setCampaign(updated);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record impression';
      addToast('error', 'Telemetry Error', msg);
    }
  };

  // Telemetry: Simulate Click
  const handleSimulateClick = async () => {
    if (!campaign) return;
    const placementId = `pl_${campaign.id}`;
    try {
      await sponsorApi.recordClick(placementId);
      addToast('info', 'Click Recorded', 'Logged engagement click telemetry event.');
      // Refresh analytics
      const updated = await sponsorApi.getCampaign(campaign.id);
      setCampaign(updated);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record click';
      addToast('error', 'Telemetry Error', msg);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="text-arcade-lime border border-arcade-lime/40 bg-arcade-lime/10 px-2.5 py-0.5 rounded font-bold text-xs tracking-wider flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-arcade-lime animate-pulse" />
            ACTIVE
          </span>
        );
      case 'FUNDED':
        return (
          <span className="text-arcade-cyan border border-arcade-cyan/40 bg-arcade-cyan/10 px-2.5 py-0.5 rounded font-bold text-xs tracking-wider">
            FUNDED
          </span>
        );
      case 'PAYMENT_PENDING':
        return (
          <span className="text-arcade-warning border border-arcade-warning/40 bg-arcade-warning/10 px-2.5 py-0.5 rounded font-bold text-xs tracking-wider">
            PAYMENT PENDING
          </span>
        );
      case 'PAYMENT_FAILED':
        return (
          <span className="text-arcade-danger border border-arcade-danger/40 bg-arcade-danger/10 px-2.5 py-0.5 rounded font-bold text-xs tracking-wider">
            PAYMENT FAILED
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="text-arcade-subtle border border-arcade-border bg-arcade-panel px-2.5 py-0.5 rounded text-xs tracking-wider">
            EXPIRED
          </span>
        );
      default:
        return (
          <span className="text-arcade-muted border border-arcade-border px-2.5 py-0.5 rounded text-xs tracking-wider">
            DRAFT
          </span>
        );
    }
  };

  if (loading) {
    return (
      <PageContainer maxWidth="md" className="py-12">
        <LoadingState message="FETCHING CAMPAIGN STATUS &amp; ESCROW LEDGER..." />
      </PageContainer>
    );
  }

  if (error || !campaign) {
    return (
      <PageContainer maxWidth="md" className="space-y-6">
        <div className="flex items-center gap-3 pb-4 border-b border-arcade-border">
          <Link to="/sponsor" className="text-arcade-muted hover:text-arcade-text p-1">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="font-display text-xl text-arcade-danger">CAMPAIGN NOT FOUND</h1>
        </div>

        <Panel header="ERROR">
          <div className="p-4 text-center space-y-3 font-mono text-xs">
            <AlertTriangle className="w-8 h-8 text-arcade-danger mx-auto" />
            <p className="text-arcade-muted">{error || `Campaign #${id} does not exist.`}</p>
            <Link to="/sponsor">
              <ArcadeButton variant="secondary" size="sm">
                RETURN TO SPONSOR PORTAL
              </ArcadeButton>
            </Link>
          </div>
        </Panel>
      </PageContainer>
    );
  }

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* Toast notifications */}
      <Toast toasts={toasts} onDismiss={dismissToast} />

      {/* Header */}
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
            <div className="flex items-center gap-2">
              <h1 className="font-display text-xl text-arcade-lime tracking-wider">
                CAMPAIGN #{campaign.id}
              </h1>
              {getStatusBadge(campaign.status)}
            </div>
            <p className="text-xs font-mono text-arcade-muted mt-0.5">
              REAL-TIME ATTENTION TELEMETRY &bull; ESCROW STATUS
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ArcadeButton
            variant="secondary"
            size="sm"
            onClick={loadCampaignData}
            title="Refresh status & telemetry"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </ArcadeButton>

          {sponsor?.website && (
            <a
              href={sponsor.website}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-mono text-arcade-muted hover:text-arcade-lime border border-arcade-border px-2.5 py-1.5 rounded transition-colors"
            >
              <span>VISIT SPONSOR</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Telemetry Metrics Grid (Always accessible for live monitoring) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono">
        <Panel header="IMPRESSIONS">
          <div className="text-center py-3">
            <div className="flex items-center justify-center gap-1.5 text-arcade-subtle text-[10px] uppercase mb-1">
              <Eye className="w-3.5 h-3.5 text-arcade-lime" />
              <span>VERIFIED DISPLAYS</span>
            </div>
            <div className="font-display text-2xl text-arcade-lime">
              {campaign.analytics?.impressions?.toLocaleString() ?? 0}
            </div>
          </div>
        </Panel>

        <Panel header="CLICKS">
          <div className="text-center py-3">
            <div className="flex items-center justify-center gap-1.5 text-arcade-subtle text-[10px] uppercase mb-1">
              <MousePointerClick className="w-3.5 h-3.5 text-arcade-cyan" />
              <span>ENGAGEMENT EVENTS</span>
            </div>
            <div className="font-display text-2xl text-arcade-cyan">
              {campaign.analytics?.clicks?.toLocaleString() ?? 0}
            </div>
          </div>
        </Panel>

        <Panel header="CLICK-THROUGH RATE">
          <div className="text-center py-3">
            <div className="flex items-center justify-center gap-1.5 text-arcade-subtle text-[10px] uppercase mb-1">
              <Sparkles className="w-3.5 h-3.5 text-arcade-pink" />
              <span>ATTENTION CONVERSION</span>
            </div>
            <div className="font-display text-2xl text-arcade-pink">
              {campaign.analytics?.click_through_rate?.toFixed(1) ?? '0.0'}%
            </div>
          </div>
        </Panel>
      </div>

      {/* Campaign Lifecycle Management Panel */}
      <Panel header="CAMPAIGN LIFECYCLE &amp; ACTIONS">
        <div className="space-y-4 font-mono text-xs">
          {/* Metadata table */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <div className="flex justify-between p-2 rounded bg-arcade-bg border border-arcade-border/50">
              <span className="text-arcade-subtle">SPONSOR BRAND</span>
              <span className="text-arcade-text font-bold">{sponsor?.name || campaign.sponsor_id}</span>
            </div>

            <div className="flex justify-between p-2 rounded bg-arcade-bg border border-arcade-border/50">
              <span className="text-arcade-subtle">TARGET PLACEMENT</span>
              <span className="text-arcade-text font-bold">{campaign.placement}</span>
            </div>

            <div className="flex justify-between p-2 rounded bg-arcade-bg border border-arcade-border/50">
              <span className="text-arcade-subtle">ESCROW BUDGET</span>
              <span className="text-arcade-lime font-bold">{campaign.budget} MON</span>
            </div>

            <div className="flex justify-between p-2 rounded bg-arcade-bg border border-arcade-border/50">
              <span className="text-arcade-subtle">ACTIVE TIMELINE</span>
              <span className="text-arcade-muted">
                {campaign.start_at
                  ? new Date(campaign.start_at).toLocaleDateString()
                  : 'PENDING'} &rarr;{' '}
                {campaign.end_at
                  ? new Date(campaign.end_at).toLocaleDateString()
                  : 'PENDING'}
              </span>
            </div>
          </div>

          {/* Transaction State for ongoing actions */}
          <TransactionState
            status={txStatus}
            txHash={txHash}
            errorMessage={txErrorMessage}
            onRetry={handleInitiateFunding}
          />

          {/* Contextual Action Bar according to status */}
          <div className="pt-2 space-y-3">
            {campaign.status === 'DRAFT' && (
              <div className="p-3 rounded bg-arcade-bg border border-arcade-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="font-semibold text-arcade-text">CAMPAIGN IN DRAFT</div>
                  <p className="text-[11px] text-arcade-subtle font-sans">
                    Lock escrow deposit to transition to payment pending.
                  </p>
                </div>
                <ArcadeButton
                  variant="primary"
                  size="sm"
                  onClick={handleInitiateFunding}
                  isLoading={actionLoading}
                  disabled={actionLoading}
                >
                  <Lock className="w-3.5 h-3.5 mr-1" />
                  INITIATE ESCROW FUNDING
                </ArcadeButton>
              </div>
            )}

            {campaign.status === 'PAYMENT_PENDING' && (
              <div className="p-3.5 rounded bg-arcade-bg border border-arcade-warning/40 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-arcade-warning uppercase text-[11px]">
                    ESCROW DEPOSIT PENDING CONFIRMATION
                  </span>
                  <span className="text-[10px] text-arcade-subtle">MOCK BLOCKCHAIN</span>
                </div>
                <p className="text-[11px] font-sans text-arcade-muted leading-relaxed">
                  Submit simulated deposit transaction to confirm escrow and advance to FUNDED state.
                </p>

                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <ArcadeButton
                    variant="primary"
                    size="sm"
                    onClick={handleConfirmFunding}
                    isLoading={actionLoading}
                    disabled={actionLoading}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                    CONFIRM MOCK DEPOSIT ({campaign.budget} MON)
                  </ArcadeButton>

                  <ArcadeButton
                    variant="danger"
                    size="sm"
                    onClick={handleSimulateFailure}
                    disabled={actionLoading}
                  >
                    <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                    SIMULATE FAILURE
                  </ArcadeButton>
                </div>
              </div>
            )}

            {campaign.status === 'PAYMENT_FAILED' && (
              <div className="p-3.5 rounded bg-arcade-bg border border-arcade-danger/40 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-arcade-danger uppercase text-[11px]">
                    PAYMENT REJECTED / FAILED
                  </span>
                  <span className="text-[10px] text-arcade-subtle">RECOVERABLE</span>
                </div>
                <p className="text-[11px] font-sans text-arcade-muted leading-relaxed">
                  Deposit did not complete. You can safely retry payment initiation to restore pending state.
                </p>

                <ArcadeButton
                  variant="danger"
                  size="sm"
                  onClick={handleInitiateFunding}
                  isLoading={actionLoading}
                  disabled={actionLoading}
                >
                  <RefreshCw className="w-3.5 h-3.5 mr-1" />
                  RETRY PAYMENT INITIATION
                </ArcadeButton>
              </div>
            )}

            {campaign.status === 'FUNDED' && (
              <div className="p-3.5 rounded bg-arcade-bg border border-arcade-cyan/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="font-semibold text-arcade-cyan">ESCROW LOCKED &amp; VERIFIED</div>
                  <p className="text-[11px] text-arcade-subtle font-sans">
                    Budget is secured in mock vault. Activate placement to begin live attention delivery.
                  </p>
                </div>
                <ArcadeButton
                  variant="primary"
                  size="sm"
                  onClick={handleActivateCampaign}
                  isLoading={actionLoading}
                  disabled={actionLoading}
                >
                  <Sparkles className="w-3.5 h-3.5 mr-1" />
                  ACTIVATE PLACEMENT
                </ArcadeButton>
              </div>
            )}

            {campaign.status === 'ACTIVE' && (
              <div className="p-3.5 rounded bg-arcade-bg border border-arcade-lime/40 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-arcade-lime uppercase text-[11px] flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-arcade-lime animate-pulse" />
                    PLACEMENT CURRENTLY LIVE ON MON ARCADE
                  </span>
                  <span className="text-[10px] text-arcade-muted font-mono">{campaign.placement}</span>
                </div>

                {/* Telemetry testing buttons */}
                <div className="border-t border-arcade-border/50 pt-2.5 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[11px] text-arcade-subtle">TEST TELEMETRY INGESTION:</span>
                  <div className="flex items-center gap-2">
                    <ArcadeButton
                      variant="secondary"
                      size="sm"
                      onClick={handleSimulateImpression}
                      title="Simulate display event"
                    >
                      <Eye className="w-3.5 h-3.5 mr-1 text-arcade-lime" />
                      SIMULATE IMPRESSION
                    </ArcadeButton>

                    <ArcadeButton
                      variant="secondary"
                      size="sm"
                      onClick={handleSimulateClick}
                      title="Simulate click event"
                    >
                      <MousePointerClick className="w-3.5 h-3.5 mr-1 text-arcade-cyan" />
                      SIMULATE CLICK
                    </ArcadeButton>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </Panel>

      {/* Escrow Vault & Settlement Record */}
      <Panel header="ESCROW VAULT &amp; SETTLEMENT AUDIT">
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between p-2 rounded bg-arcade-bg border border-arcade-border/60">
            <span className="text-arcade-subtle">ESCROW VAULT ID</span>
            <span className="text-arcade-text font-bold">
              {campaign.vault?.id || 'UNASSIGNED'}
            </span>
          </div>

          <div className="flex items-center justify-between p-2 rounded bg-arcade-bg border border-arcade-border/60">
            <span className="text-arcade-subtle">SETTLEMENT ENVIRONMENT</span>
            <span className="text-arcade-cyan font-bold flex items-center gap-1">
              <Shield className="w-3.5 h-3.5" />
              monad-mock-local
            </span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between p-2 rounded bg-arcade-bg border border-arcade-border/60 gap-1">
            <span className="text-arcade-subtle shrink-0">DEPOSIT TX HASH</span>
            <span className="text-arcade-lime break-all select-all font-mono text-[11px]">
              {campaign.vault?.deposit_tx || 'NO SETTLEMENT RECORDED'}
            </span>
          </div>

          {/* Strict Mock Disclosure per project rules */}
          <div className="p-3 rounded bg-arcade-panel border border-arcade-lime/30 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-arcade-lime" />
              <span className="text-[11px] text-arcade-lime font-bold tracking-wider">
                [MOCK / LOCAL SETTLEMENT]
              </span>
            </div>
            <span className="text-[10px] text-arcade-subtle font-sans">
              Authoritative local ledger in simulation mode.
            </span>
          </div>
        </div>
      </Panel>

      {/* Subordinate Placement Live Preview */}
      <Panel header="LIVE SUBORDINATE BANNER PREVIEW">
        <div className="space-y-3">
          <p className="text-xs text-arcade-muted leading-relaxed font-sans">
            How your sponsor badge appears on the <code className="text-arcade-text">{campaign.placement}</code> screen.
            Notice how it maintains clean restraint and subordinate presence relative to the arcade gameplay:
          </p>

          <div className="p-3.5 rounded bg-arcade-bg border border-arcade-border/80">
            <SponsorBadge
              name={sponsor?.name || 'MON ARCADE'}
              tagline={sponsor ? (campaign.placement ? `OFFICIAL SPONSOR OF ${campaign.placement}` : sponsor.website) : 'HIGH-PERFORMANCE ON-CHAIN ENTERTAINMENT'}
              url={sponsor?.website || 'https://monad.xyz'}
            />
          </div>
        </div>
      </Panel>
    </PageContainer>
  );
};
