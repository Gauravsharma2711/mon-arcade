-- Mon Arcade Migration 004: Sponsor System Persistence
-- Extended schema for Sponsor wallets/logos, Campaign lifecycle states, Sponsor Vault escrow, and Analytics.

ALTER TABLE sponsors
    ADD COLUMN IF NOT EXISTS wallet VARCHAR(42) DEFAULT '0x0000000000000000000000000000000000000000',
    ADD COLUMN IF NOT EXISTS logo VARCHAR(512);

ALTER TABLE campaigns
    ADD COLUMN IF NOT EXISTS placement VARCHAR(64) DEFAULT 'MARQUEE',
    ADD COLUMN IF NOT EXISTS start_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS end_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS start_time TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS end_time TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Sponsor Vault: Authoritative escrow record holding deposited campaign funds
CREATE TABLE IF NOT EXISTS sponsor_vaults (
    id VARCHAR(64) PRIMARY KEY,
    campaign_id VARCHAR(64) REFERENCES campaigns(id) ON DELETE CASCADE,
    deposit_tx VARCHAR(66),
    deposit_transaction VARCHAR(66),
    amount NUMERIC(20, 8) NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'FUNDED', 'RELEASED', 'REFUNDED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sponsor_vaults_campaign_id ON sponsor_vaults(campaign_id);

-- Campaign Analytics: Verified attention metrics (impressions, clicks, timestamp)
CREATE TABLE IF NOT EXISTS campaign_analytics (
    id VARCHAR(64) PRIMARY KEY,
    campaign_id VARCHAR(64) REFERENCES campaigns(id) ON DELETE CASCADE,
    impressions INT NOT NULL DEFAULT 0,
    clicks INT NOT NULL DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_campaign_analytics_campaign_id ON campaign_analytics(campaign_id);
