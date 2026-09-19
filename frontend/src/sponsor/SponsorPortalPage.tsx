import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { PageContainer } from '../components/PageContainer';
import { Panel } from '../components/Panel';
import { ArcadeButton } from '../components/ArcadeButton';
import { SponsorBadge } from '../components/SponsorBadge';
import { LoadingState } from '../components/LoadingState';
import { Plus, ArrowRight, Layers, Sparkles, RefreshCw } from 'lucide-react';
import { sponsorApi, CampaignDetailData } from '../lib/sponsorApi';
import { PlacementSlot } from './types';

export const SponsorPortalPage: React.FC = () => {
  const [campaigns, setCampaigns] = useState<CampaignDetailData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [previewSlot, setPreviewSlot] = useState<PlacementSlot>('HOME_MARQUEE');

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const data = await sponsorApi.listCampaigns();
      setCampaigns(data);
    } catch (err) {
      console.warn('Could not fetch campaigns:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return <span className="text-arcade-lime border border-arcade-lime/40 bg-arcade-lime/10 px-2 py-0.5 rounded font-bold text-[10px] tracking-wider">ACTIVE</span>;
      case 'FUNDED':
        return <span className="text-arcade-cyan border border-arcade-cyan/40 bg-arcade-cyan/10 px-2 py-0.5 rounded font-bold text-[10px] tracking-wider">FUNDED</span>;
      case 'PAYMENT_PENDING':
        return <span className="text-arcade-warning border border-arcade-warning/40 bg-arcade-warning/10 px-2 py-0.5 rounded font-bold text-[10px] tracking-wider">PAYMENT PENDING</span>;
      case 'PAYMENT_FAILED':
        return <span className="text-arcade-danger border border-arcade-danger/40 bg-arcade-danger/10 px-2 py-0.5 rounded font-bold text-[10px] tracking-wider">PAYMENT FAILED</span>;
      case 'EXPIRED':
        return <span className="text-arcade-subtle border border-arcade-border bg-arcade-panel px-2 py-0.5 rounded text-[10px] tracking-wider">EXPIRED</span>;
      default:
        return <span className="text-arcade-muted border border-arcade-border px-2 py-0.5 rounded text-[10px] tracking-wider">DRAFT</span>;
    }
  };

  return (
    <PageContainer maxWidth="md" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-arcade-border gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-xl text-arcade-lime tracking-wider">
              SPONSOR PORTAL
            </h1>
            <span className="text-[10px] font-mono border border-arcade-lime/30 text-arcade-lime/80 px-1.5 py-0.5 rounded">
              LOCAL DEV
            </span>
          </div>
          <p className="text-xs font-mono text-arcade-muted mt-1">
            SUBORDINATE MARQUEE PLACEMENTS &bull; HIGH ATTENTION ON MONAD
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ArcadeButton
            variant="secondary"
            size="sm"
            onClick={loadCampaigns}
            title="Refresh campaign ledger"
            aria-label="Refresh campaigns"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </ArcadeButton>
          <Link to="/sponsor/create">
            <ArcadeButton variant="primary" size="sm">
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              NEW CAMPAIGN
            </ArcadeButton>
          </Link>
        </div>
      </div>

      {/* Screen Location Preview */}
      <Panel header="SUBORDINATE PLACEMENT PREVIEW">
        <div className="space-y-4">
          <p className="text-xs text-arcade-muted leading-relaxed">
            Per the Mon Arcade hierarchy (<code className="text-arcade-text">Game &gt; Game Action &gt; Game State &gt; Sponsor</code>), sponsor banners appear secondary to gameplay and never obstruct controls or change game rules.
          </p>

          <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
            <button
              onClick={() => setPreviewSlot('HOME_MARQUEE')}
              className={`px-3 py-1.5 rounded border transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-lime ${
                previewSlot === 'HOME_MARQUEE'
                  ? 'border-arcade-lime text-arcade-lime bg-arcade-lime/10'
                  : 'border-arcade-border text-arcade-muted hover:text-arcade-text'
              }`}
            >
              HOME BANNER
            </button>
            <button
              onClick={() => setPreviewSlot('BLUFF_LOBBY')}
              className={`px-3 py-1.5 rounded border transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-pink ${
                previewSlot === 'BLUFF_LOBBY'
                  ? 'border-arcade-pink text-arcade-pink bg-arcade-pink/10'
                  : 'border-arcade-border text-arcade-muted hover:text-arcade-text'
              }`}
            >
              BLUFF LOBBY
            </button>
            <button
              onClick={() => setPreviewSlot('VAULT_SETUP')}
              className={`px-3 py-1.5 rounded border transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-arcade-cyan ${
                previewSlot === 'VAULT_SETUP'
                  ? 'border-arcade-cyan text-arcade-cyan bg-arcade-cyan/10'
                  : 'border-arcade-border text-arcade-muted hover:text-arcade-text'
              }`}
            >
              VAULT LOADOUT
            </button>
          </div>

          <div className="p-3 rounded bg-arcade-bg/60 border border-arcade-border/60">
            <div className="text-[10px] font-mono text-arcade-subtle mb-2 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-arcade-lime" />
              SLOT: {previewSlot}
            </div>
            <SponsorBadge
              name="MON ARCADE FOUNDATION"
              tagline="HIGH-PERFORMANCE ON-CHAIN ENTERTAINMENT EXPERIMENTS"
              url="https://monad.xyz"
            />
          </div>
        </div>
      </Panel>

      {/* Active Campaigns List */}
      <Panel header="CAMPAIGN MANAGEMENT">
        {loading ? (
          <div className="py-6">
            <LoadingState message="LOADING CAMPAIGN LEDGER..." />
          </div>
        ) : campaigns.length === 0 ? (
          <div className="text-center py-8 font-mono space-y-3">
            <Layers className="w-8 h-8 text-arcade-subtle mx-auto" />
            <div className="text-arcade-text text-sm font-semibold">NO CAMPAIGNS REGISTERED</div>
            <p className="text-xs text-arcade-muted max-w-sm mx-auto">
              Create a sponsor campaign to reserve placement across the Home lobby, Bluff duels, or Vault chamber.
            </p>
            <Link to="/sponsor/create" className="inline-block pt-2">
              <ArcadeButton variant="primary" size="sm">
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                CREATE FIRST CAMPAIGN
              </ArcadeButton>
            </Link>
          </div>
        ) : (
          <div className="space-y-3 font-mono text-xs">
            {campaigns.map((c) => (
              <div
                key={c.id}
                className="p-3.5 rounded bg-arcade-bg border border-arcade-border hover:border-arcade-border/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-arcade-text tracking-wide">
                      CAMPAIGN #{c.id}
                    </span>
                    {getStatusBadge(c.status)}
                  </div>
                  <div className="text-[11px] text-arcade-subtle flex flex-wrap items-center gap-3">
                    <span>SLOT: <span className="text-arcade-text">{c.placement}</span></span>
                    <span>BUDGET: <span className="text-arcade-lime">{c.budget} MON</span></span>
                    {c.vault?.deposit_tx && (
                      <span className="text-arcade-muted truncate max-w-[140px]" title={c.vault.deposit_tx}>
                        TX: {c.vault.deposit_tx}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto justify-end pt-2 sm:pt-0 border-t sm:border-t-0 border-arcade-border/40">
                  <Link to={`/sponsor/${c.id}`} className="w-full sm:w-auto">
                    <ArcadeButton variant="secondary" size="sm" className="w-full sm:w-auto">
                      <span>MANAGE</span>
                      <ArrowRight className="w-3.5 h-3.5 ml-1" />
                    </ArcadeButton>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </PageContainer>
  );
};
