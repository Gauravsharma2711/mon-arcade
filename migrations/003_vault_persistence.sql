-- Mon Arcade Migration 003: Monad Vault Persistence
-- Authoritative server-owned state for Vault matches, turn history, agent configs, and outcomes.

ALTER TABLE vault_matches
    ADD COLUMN IF NOT EXISTS player_role VARCHAR(32) NOT NULL DEFAULT 'ATTACKER',
    ADD COLUMN IF NOT EXISTS current_turn INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS currency VARCHAR(16) NOT NULL DEFAULT 'MON',
    ADD COLUMN IF NOT EXISTS vault_state VARCHAR(32) NOT NULL DEFAULT 'LOCKED',
    ADD COLUMN IF NOT EXISTS warden_config_payload JSONB,
    ADD COLUMN IF NOT EXISTS attacker_config_payload JSONB,
    ADD COLUMN IF NOT EXISTS events_payload JSONB,
    ADD COLUMN IF NOT EXISTS result_payload JSONB,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE vault_turns
    ADD COLUMN IF NOT EXISTS acting_role VARCHAR(32) NOT NULL DEFAULT 'ATTACKER',
    ADD COLUMN IF NOT EXISTS agent_decision VARCHAR(32) NOT NULL DEFAULT 'DENY_ACCESS',
    ADD COLUMN IF NOT EXISTS dialogue_data TEXT,
    ADD COLUMN IF NOT EXISTS resulting_state VARCHAR(32) NOT NULL DEFAULT 'ACTIVE';
