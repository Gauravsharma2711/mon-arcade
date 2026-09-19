-- Mon Arcade Initial Schema Migration
-- Authoritative server-owned state for Bluff or Bust, Monad Vault, Sponsors, and Transactions.

-- 1. Users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Game Sessions (top-level session envelope)
CREATE TABLE IF NOT EXISTS game_sessions (
    id VARCHAR(64) PRIMARY KEY,
    game_type VARCHAR(32) NOT NULL, -- 'bluff' or 'vault'
    user_id VARCHAR(64) REFERENCES users(id),
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'COMPLETED', 'ABANDONED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON game_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_game_type ON game_sessions(game_type);

-- 3. Bluff Matches (1v1 hidden-information duel)
-- Game state authority strictly owned by server (secrets hidden until resolution)
CREATE TABLE IF NOT EXISTS bluff_matches (
    id VARCHAR(64) PRIMARY KEY,
    creator_id VARCHAR(64) REFERENCES users(id),
    opponent_id VARCHAR(64) REFERENCES users(id),
    stake_amount NUMERIC(20, 8) NOT NULL DEFAULT 0,
    creator_secret INT,   -- Server-owned authoritative hidden choice
    opponent_secret INT,  -- Server-owned authoritative hidden choice
    winner_id VARCHAR(64) REFERENCES users(id),
    status VARCHAR(32) NOT NULL DEFAULT 'WAITING', -- 'WAITING', 'ACTIVE', 'RESOLVED', 'CANCELLED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_bluff_matches_creator_id ON bluff_matches(creator_id);
CREATE INDEX IF NOT EXISTS idx_bluff_matches_opponent_id ON bluff_matches(opponent_id);
CREATE INDEX IF NOT EXISTS idx_bluff_matches_status ON bluff_matches(status);

-- 4. Vault Matches (Warden vs Attacker AI battle)
-- Pot, turns allowed, and breach status owned by server
CREATE TABLE IF NOT EXISTS vault_matches (
    id VARCHAR(64) PRIMARY KEY,
    challenger_id VARCHAR(64) REFERENCES users(id),
    warden_model VARCHAR(64) NOT NULL DEFAULT 'mock-warden',
    entry_fee NUMERIC(20, 8) NOT NULL DEFAULT 0,
    pot_amount NUMERIC(20, 8) NOT NULL DEFAULT 0,
    turns_allowed INT NOT NULL DEFAULT 3,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'BREACHED', 'FAILED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_vault_matches_challenger_id ON vault_matches(challenger_id);
CREATE INDEX IF NOT EXISTS idx_vault_matches_status ON vault_matches(status);

-- 5. Vault Turns (Attacker prompt, Warden response, breach evaluation)
CREATE TABLE IF NOT EXISTS vault_turns (
    id VARCHAR(64) PRIMARY KEY,
    match_id VARCHAR(64) REFERENCES vault_matches(id) ON DELETE CASCADE,
    turn_number INT NOT NULL,
    attacker_prompt TEXT NOT NULL,
    warden_response TEXT NOT NULL,
    breach_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_vault_turns_match_id ON vault_turns(match_id);

-- 6. Sponsors
CREATE TABLE IF NOT EXISTS sponsors (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    tagline VARCHAR(256) NOT NULL,
    url VARCHAR(512) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id VARCHAR(64) PRIMARY KEY,
    sponsor_id VARCHAR(64) REFERENCES sponsors(id),
    name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'PAUSED', 'ENDED'
    budget NUMERIC(20, 8) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_campaigns_sponsor_id ON campaigns(sponsor_id);

-- 8. Placements
CREATE TABLE IF NOT EXISTS placements (
    id VARCHAR(64) PRIMARY KEY,
    campaign_id VARCHAR(64) REFERENCES campaigns(id),
    slot_type VARCHAR(64) NOT NULL, -- 'marquee', 'footer', 'game_card'
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_placements_campaign_id ON placements(campaign_id);

-- 9. Transactions (Monad actions ledger)
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES users(id),
    tx_hash VARCHAR(66) UNIQUE,
    tx_type VARCHAR(64) NOT NULL, -- 'ENTRY_FEE', 'PAYOUT', 'SPONSOR_PAYMENT'
    amount NUMERIC(20, 8) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'CONFIRMED', 'FAILED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_tx_hash ON transactions(tx_hash);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

-- 10. Impressions (telemetry)
CREATE TABLE IF NOT EXISTS impressions (
    id VARCHAR(64) PRIMARY KEY,
    placement_id VARCHAR(64) REFERENCES placements(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_impressions_placement_id ON impressions(placement_id);

-- 11. Clicks (telemetry)
CREATE TABLE IF NOT EXISTS clicks (
    id VARCHAR(64) PRIMARY KEY,
    placement_id VARCHAR(64) REFERENCES placements(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_clicks_placement_id ON clicks(placement_id);
