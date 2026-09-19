/**
 * Authoritative TypeScript domain models for the Mon Arcade Sponsor System.
 * Matches backend domain models, placement definitions, and explicit state machine.
 */

export type CampaignStatus =
  | 'DRAFT'
  | 'PAYMENT_PENDING'
  | 'PAYMENT_FAILED'
  | 'FUNDED'
  | 'ACTIVE'
  | 'EXPIRED';

export type SponsorVaultStatus =
  | 'PENDING'
  | 'FUNDED'
  | 'RELEASED'
  | 'REFUNDED';

export type PlacementSlot =
  | 'HOME_MARQUEE'
  | 'BLUFF_LOBBY'
  | 'VAULT_SETUP'
  | 'MARQUEE'
  | 'FOOTER'
  | 'GAME_CARD';

export interface Sponsor {
  sponsor_id: string;
  name: string;
  wallet: string;
  logo?: string | null;
  website: string;
  created_at?: string;
}

export interface Campaign {
  campaign_id: string;
  sponsor_id: string;
  placement: PlacementSlot;
  start_time?: string | null;
  end_time?: string | null;
  budget: number | string;
  status: CampaignStatus;
  created_at?: string;
  updated_at?: string;
}

export interface Placement {
  placement_id: string;
  campaign_id: string;
  slot_type: PlacementSlot;
  active: boolean;
  created_at?: string;
}

export interface SponsorVault {
  vault_id: string;
  campaign_id: string;
  deposit_transaction?: string | null;
  amount: number | string;
  status: SponsorVaultStatus;
  created_at?: string;
  updated_at?: string;
}

export interface Analytics {
  campaign_id: string;
  impressions: number;
  clicks: number;
  timestamp: string;
  click_through_rate?: number;
}

export interface ResolvedSponsor {
  placement_id: string;
  campaign_id?: string | null;
  sponsor_id: string;
  name: string;
  tagline: string;
  url: string;
  logo?: string | null;
  slot_type: PlacementSlot;
  is_fallback: boolean;
}
