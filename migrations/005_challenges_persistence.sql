-- Mon Arcade Migration 005: Arcade Challenges & MON Bounties
-- Authoritative server-owned state for Vault challenges, conditions, and bounty claims.

CREATE TABLE IF NOT EXISTS arcade_challenges (
    id VARCHAR(64) PRIMARY KEY,
    creator_wallet VARCHAR(42) NOT NULL,
    game VARCHAR(32) NOT NULL DEFAULT 'VAULT',
    condition VARCHAR(64) NOT NULL DEFAULT 'ATTACKER_WINS',
    bounty_amount NUMERIC(20, 8) NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    accepted_by VARCHAR(42),
    winner_wallet VARCHAR(42),
    match_id VARCHAR(64) REFERENCES vault_matches(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    claimed_at TIMESTAMP WITH TIME ZONE,
    claim_tx_hash VARCHAR(66)
);

CREATE INDEX IF NOT EXISTS idx_arcade_challenges_status ON arcade_challenges(status);
CREATE INDEX IF NOT EXISTS idx_arcade_challenges_creator ON arcade_challenges(creator_wallet);
CREATE INDEX IF NOT EXISTS idx_arcade_challenges_match ON arcade_challenges(match_id);
