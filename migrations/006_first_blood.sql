-- Mon Arcade Migration 006: First Blood / Early Arcade Player
-- Minimal, immutable record of a player's first game participation.

CREATE TABLE IF NOT EXISTS first_blood_players (
    wallet VARCHAR(42) PRIMARY KEY,
    first_participation_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    player_number SERIAL,
    first_game VARCHAR(32) NOT NULL DEFAULT 'VAULT'
);

CREATE INDEX IF NOT EXISTS idx_first_blood_wallet ON first_blood_players(wallet);
