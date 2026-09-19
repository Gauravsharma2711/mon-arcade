/**
 * Client API for Mon Arcade Sponsor system.
 * Handles sponsor registration, campaign creation, funding flow,
 * telemetry events, and active placement resolution.
 */

import {
  Sponsor,
  CampaignStatus,
} from '../sponsor/types';

export interface CreateSponsorInput {
  name: string;
  wallet: string;
  website: string;
  logo?: string | null;
}

export interface CreateCampaignInput {
  sponsor_id: string;
  placement: string;
  budget: number;
  start_at?: string | null;
  end_at?: string | null;
  auto_fund?: boolean;
}

export interface CampaignDetailData {
  id: string;
  sponsor_id: string;
  placement: string;
  budget: number;
  status: CampaignStatus;
  start_at?: string | null;
  end_at?: string | null;
  created_at?: string | null;
  vault?: {
    id: string;
    amount: number;
    deposit_tx?: string | null;
    status: string;
    is_mock?: boolean;
    chain?: string;
  } | null;
  analytics?: {
    impressions: number;
    clicks: number;
    click_through_rate: number;
  } | null;
}

export interface FundingInitiationData {
  campaign_id: string;
  status: string;
  budget: number;
  currency: string;
  chain: string;
  is_mock: boolean;
  deposit_recipient: string;
  instructions: string;
}

export const sponsorApi = {
  async createSponsor(input: CreateSponsorInput): Promise<Sponsor> {
    const res = await fetch('/api/sponsor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create sponsor' }));
      throw new Error(err.detail || 'Failed to create sponsor');
    }
    const data = await res.json();
    return {
      sponsor_id: data.id,
      name: data.name,
      wallet: data.wallet,
      website: data.website,
      logo: data.logo,
      created_at: data.created_at,
    };
  },

  async getSponsor(sponsorId: string): Promise<Sponsor> {
    const res = await fetch(`/api/sponsor/entity/${encodeURIComponent(sponsorId)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Sponsor not found' }));
      throw new Error(err.detail || 'Sponsor not found');
    }
    const data = await res.json();
    return {
      sponsor_id: data.id,
      name: data.name,
      wallet: data.wallet,
      website: data.website,
      logo: data.logo,
      created_at: data.created_at,
    };
  },

  async createCampaign(input: CreateCampaignInput): Promise<CampaignDetailData> {
    const res = await fetch('/api/sponsor/campaign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create campaign' }));
      throw new Error(err.detail || 'Failed to create campaign');
    }
    return res.json();
  },

  async getCampaign(id: string): Promise<CampaignDetailData> {
    const res = await fetch(`/api/sponsor/campaign/${encodeURIComponent(id)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Campaign not found' }));
      throw new Error(err.detail || 'Campaign not found');
    }
    return res.json();
  },

  async listCampaigns(sponsorId?: string): Promise<CampaignDetailData[]> {
    const url = sponsorId
      ? `/api/sponsor/campaigns?sponsor_id=${encodeURIComponent(sponsorId)}`
      : '/api/sponsor/campaigns';
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error('Failed to fetch campaigns');
    }
    return res.json();
  },

  async initiateFunding(campaignId: string): Promise<FundingInitiationData> {
    const res = await fetch(`/api/sponsor/campaign/${encodeURIComponent(campaignId)}/initiate-funding`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to initiate funding' }));
      throw new Error(err.detail || 'Failed to initiate funding');
    }
    return res.json();
  },

  async confirmFunding(
    campaignId: string,
    payload?: { tx_hash?: string; auto_activate?: boolean }
  ): Promise<CampaignDetailData> {
    const res = await fetch(`/api/sponsor/campaign/${encodeURIComponent(campaignId)}/confirm-funding`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || { auto_activate: true }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to confirm funding' }));
      throw new Error(err.detail || 'Failed to confirm funding');
    }
    return res.json();
  },

  async failFunding(campaignId: string, reason?: string): Promise<CampaignDetailData> {
    const res = await fetch(`/api/sponsor/campaign/${encodeURIComponent(campaignId)}/fail-funding`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason || 'User requested payment failure test' }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to mark funding failed' }));
      throw new Error(err.detail || 'Failed to mark funding failed');
    }
    return res.json();
  },

  async activateCampaign(campaignId: string): Promise<CampaignDetailData> {
    const res = await fetch(`/api/sponsor/campaign/${encodeURIComponent(campaignId)}/activate`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to activate campaign' }));
      throw new Error(err.detail || 'Failed to activate campaign');
    }
    return res.json();
  },

  async getActiveSponsor(placementType: string = 'marquee') {
    const res = await fetch(`/api/sponsor/active?placement_type=${encodeURIComponent(placementType)}`);
    if (!res.ok) {
      throw new Error('Failed to resolve active sponsor');
    }
    return res.json();
  },

  async recordImpression(placementId: string): Promise<{ status: string; recorded: boolean }> {
    const res = await fetch(`/api/sponsor/impression/${encodeURIComponent(placementId)}`, {
      method: 'POST',
    });
    if (!res.ok) {
      throw new Error('Failed to record impression');
    }
    return res.json();
  },

  async recordClick(placementId: string): Promise<{ status: string; recorded: boolean }> {
    const res = await fetch(`/api/sponsor/click/${encodeURIComponent(placementId)}`, {
      method: 'POST',
    });
    if (!res.ok) {
      throw new Error('Failed to record click');
    }
    return res.json();
  },
};
