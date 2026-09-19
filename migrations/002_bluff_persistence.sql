-- Mon Arcade Migration 002: Bluff or Bust Persistence
-- Authoritative server-owned state for commitments, countdowns, actions, and results.

ALTER TABLE bluff_matches
    ADD COLUMN IF NOT EXISTS pot_amount NUMERIC(20, 8) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS creator_salt VARCHAR(128),
    ADD COLUMN IF NOT EXISTS creator_commitment_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS creator_has_committed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS creator_action VARCHAR(32),
    ADD COLUMN IF NOT EXISTS creator_action_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS opponent_salt VARCHAR(128),
    ADD COLUMN IF NOT EXISTS opponent_commitment_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS opponent_has_committed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS opponent_action VARCHAR(32),
    ADD COLUMN IF NOT EXISTS opponent_action_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS active_turn_player_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS turn_deadline TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS turn_seconds_allowed INT NOT NULL DEFAULT 15,
    ADD COLUMN IF NOT EXISTS resolution_reason VARCHAR(64),
    ADD COLUMN IF NOT EXISTS payout_tx_hash VARCHAR(128),
    ADD COLUMN IF NOT EXISTS result_payload JSONB,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
