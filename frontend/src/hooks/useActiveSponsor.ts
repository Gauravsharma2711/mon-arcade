import { useState, useEffect, useRef } from 'react';
import { PlacementSlot } from '../sponsor/types';

export interface ActiveSponsor {
  id: string;
  name: string;
  tagline: string;
  url: string;
  is_fallback: boolean;
  placement_id?: string;
  campaign_id?: string | null;
  logo?: string | null;
}

const DEFAULT_FALLBACK_SPONSOR: ActiveSponsor = {
  id: 'fallback-mon-arcade',
  name: 'MON ARCADE',
  tagline: 'HIGH-PERFORMANCE ON-CHAIN ENTERTAINMENT EXPERIMENTS',
  url: 'https://monad.xyz',
  is_fallback: true,
};

/**
 * Hook to resolve active sponsor content for a specific Mon Arcade placement slot.
 * Completely isolated from game logic.
 * 
 * Rules:
 * - Non-blocking: loading or API errors never freeze or delay UI.
 * - Automatic graceful fallback to Mon Arcade default branding.
 * - Non-intrusive impression & click tracking for real active campaigns.
 */
export function useActiveSponsor(slotType: PlacementSlot | string = 'HOME_MARQUEE') {
  const [sponsor, setSponsor] = useState<ActiveSponsor>(DEFAULT_FALLBACK_SPONSOR);
  const [loading, setLoading] = useState<boolean>(true);
  const recordedImpressionRef = useRef<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchSponsor() {
      try {
        const response = await fetch(
          `/api/sponsor/active?placement_type=${encodeURIComponent(slotType)}`
        );
        if (response.ok) {
          const data: ActiveSponsor = await response.json();
          if (isMounted) {
            setSponsor(data);

            // Record verified impression asynchronously if valid active campaign placement
            if (
              !data.is_fallback &&
              data.placement_id &&
              recordedImpressionRef.current !== data.placement_id
            ) {
              recordedImpressionRef.current = data.placement_id;
              fetch(`/api/sponsor/impression/${encodeURIComponent(data.placement_id)}`, {
                method: 'POST',
              }).catch(() => {
                // Non-blocking telemetry failure is silently ignored
              });
            }
          }
        }
      } catch {
        // Non-blocking network error: default fallback branding remains active
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    fetchSponsor();

    return () => {
      isMounted = false;
    };
  }, [slotType]);

  const recordClick = () => {
    if (!sponsor.is_fallback && sponsor.placement_id) {
      fetch(`/api/sponsor/click/${encodeURIComponent(sponsor.placement_id)}`, {
        method: 'POST',
      }).catch(() => {
        // Non-blocking click telemetry failure is silently ignored
      });
    }
  };

  return { sponsor, loading, recordClick };
}
