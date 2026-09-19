import { useState, useCallback, useMemo } from 'react';
import {
  vaultApi,
  VaultRole,
  AttackerStatAllocation,
  WardenStatAllocation,
  VaultApiError,
} from '../lib/vaultApi';

export const TOTAL_STAT_BUDGET = 100;
export const DEFAULT_ENTRY_FEE = 2.5;
export const DEFAULT_POT_AMOUNT = 250.0;

export const DEFAULT_ATTACKER_STATS: AttackerStatAllocation = {
  persuasion: 25,
  deception: 25,
  patience: 25,
  aggression: 25,
};

export const DEFAULT_WARDEN_STATS: WardenStatAllocation = {
  skepticism: 25,
  rigidity: 25,
  empathy: 25,
  memory: 25,
};

export function getOrCreateVaultPlayerId(): string {
  if (typeof window === 'undefined') return '0x71aVaultChallenger9b2';
  const stored = localStorage.getItem('mon_arcade_vault_player_id');
  if (stored) return stored;

  const randomHex = Array.from({ length: 8 }, () =>
    Math.floor(Math.random() * 16).toString(16)
  ).join('');
  const newId = `0x71a${randomHex}9b2`;
  localStorage.setItem('mon_arcade_vault_player_id', newId);
  return newId;
}

export function useVaultSetup() {
  const [playerId] = useState<string>(getOrCreateVaultPlayerId);
  const [selectedRole, setSelectedRole] = useState<VaultRole>('ATTACKER');
  const [attackerStats, setAttackerStats] = useState<AttackerStatAllocation>(DEFAULT_ATTACKER_STATS);
  const [wardenStats, setWardenStats] = useState<WardenStatAllocation>(DEFAULT_WARDEN_STATS);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Active stats based on selected role
  const currentStats = useMemo(() => {
    return selectedRole === 'ATTACKER' ? attackerStats : wardenStats;
  }, [selectedRole, attackerStats, wardenStats]);

  // Total allocated points
  const allocatedPoints = useMemo(() => {
    if (selectedRole === 'ATTACKER') {
      return (
        attackerStats.persuasion +
        attackerStats.deception +
        attackerStats.patience +
        attackerStats.aggression
      );
    } else {
      return (
        wardenStats.skepticism +
        wardenStats.rigidity +
        wardenStats.empathy +
        wardenStats.memory
      );
    }
  }, [selectedRole, attackerStats, wardenStats]);

  const remainingPoints = TOTAL_STAT_BUDGET - allocatedPoints;
  const isValidAllocation = allocatedPoints === TOTAL_STAT_BUDGET;

  // Stat Adjuster with boundaries [0, 100]
  const adjustStat = useCallback(
    (key: string, delta: number) => {
      setError(null);
      if (selectedRole === 'ATTACKER') {
        setAttackerStats((prev) => {
          const current = prev[key as keyof AttackerStatAllocation];
          const updated = Math.max(0, Math.min(100, current + delta));
          return { ...prev, [key]: updated };
        });
      } else {
        setWardenStats((prev) => {
          const current = prev[key as keyof WardenStatAllocation];
          const updated = Math.max(0, Math.min(100, current + delta));
          return { ...prev, [key]: updated };
        });
      }
    },
    [selectedRole]
  );

  // Direct set
  const setStatValue = useCallback(
    (key: string, value: number) => {
      setError(null);
      const clamped = Math.max(0, Math.min(100, isNaN(value) ? 0 : Math.round(value)));
      if (selectedRole === 'ATTACKER') {
        setAttackerStats((prev) => ({ ...prev, [key]: clamped }));
      } else {
        setWardenStats((prev) => ({ ...prev, [key]: clamped }));
      }
    },
    [selectedRole]
  );

  // Presets
  const applyBalancedPreset = useCallback(() => {
    setError(null);
    if (selectedRole === 'ATTACKER') {
      setAttackerStats(DEFAULT_ATTACKER_STATS);
    } else {
      setWardenStats(DEFAULT_WARDEN_STATS);
    }
  }, [selectedRole]);

  const applySpecializedPreset = useCallback(
    (presetName: string) => {
      setError(null);
      if (selectedRole === 'ATTACKER') {
        if (presetName === 'persuasion') {
          setAttackerStats({ persuasion: 55, deception: 25, patience: 10, aggression: 10 });
        } else if (presetName === 'deception') {
          setAttackerStats({ deception: 55, persuasion: 25, patience: 10, aggression: 10 });
        } else if (presetName === 'aggression') {
          setAttackerStats({ aggression: 55, persuasion: 20, deception: 15, patience: 10 });
        }
      } else {
        if (presetName === 'skepticism') {
          setWardenStats({ skepticism: 55, rigidity: 25, memory: 15, empathy: 5 });
        } else if (presetName === 'rigidity') {
          setWardenStats({ rigidity: 55, skepticism: 25, memory: 15, empathy: 5 });
        } else if (presetName === 'memory') {
          setWardenStats({ memory: 50, skepticism: 30, rigidity: 15, empathy: 5 });
        }
      }
    },
    [selectedRole]
  );

  // Authoritative match creation & launch
  const startBattle = useCallback(async (): Promise<string> => {
    if (!isValidAllocation) {
      const diff = TOTAL_STAT_BUDGET - allocatedPoints;
      const msg =
        diff > 0
          ? `Please allocate all ${TOTAL_STAT_BUDGET} points before entering battle (${diff} points unspent).`
          : `Point budget exceeded by ${Math.abs(diff)} points. Total must equal ${TOTAL_STAT_BUDGET}.`;
      setError(msg);
      throw new Error(msg);
    }

    setIsLoading(true);
    setError(null);

    try {
      // 1. Authoritatively create the Vault match
      const match = await vaultApi.createMatch({
        player_id: playerId,
        player_role: selectedRole,
        entry_fee: DEFAULT_ENTRY_FEE,
        pot_amount: DEFAULT_POT_AMOUNT,
        attacker_stats: attackerStats,
        warden_stats: wardenStats,
      });

      // 2. Start the battle chamber (SETUP -> ACTIVE)
      await vaultApi.startMatch(match.id, playerId);

      setIsLoading(false);
      return match.id;
    } catch (err: any) {
      setIsLoading(false);
      const detail = err instanceof VaultApiError ? err.detail : err.message || 'Failed to initiate battle chamber';
      setError(detail);
      throw err;
    }
  }, [allocatedPoints, isValidAllocation, playerId, selectedRole, attackerStats, wardenStats]);

  return {
    playerId,
    selectedRole,
    setSelectedRole,
    attackerStats,
    wardenStats,
    currentStats,
    allocatedPoints,
    remainingPoints,
    isValidAllocation,
    adjustStat,
    setStatValue,
    applyBalancedPreset,
    applySpecializedPreset,
    startBattle,
    isLoading,
    error,
    setError,
  };
}
