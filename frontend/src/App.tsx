import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ArcadeShell } from './components/ArcadeShell';
import { LoadingState } from './components/LoadingState';
import { PageContainer } from './components/PageContainer';
import { HomePage } from './pages/HomePage';

// Lazy-loaded heavy game and portal routes for performance and code splitting
const BluffLobbyPage = lazy(() =>
  import('./games/bluff/BluffLobbyPage').then((m) => ({ default: m.BluffLobbyPage }))
);
const BluffMatchPage = lazy(() =>
  import('./games/bluff/BluffMatchPage').then((m) => ({ default: m.BluffMatchPage }))
);
const BluffResultPage = lazy(() =>
  import('./games/bluff/BluffResultPage').then((m) => ({ default: m.BluffResultPage }))
);
const VaultSetupPage = lazy(() =>
  import('./games/vault/VaultSetupPage').then((m) => ({ default: m.VaultSetupPage }))
);
const VaultBattlePage = lazy(() =>
  import('./games/vault/VaultBattlePage').then((m) => ({ default: m.VaultBattlePage }))
);
const VaultResultPage = lazy(() =>
  import('./games/vault/VaultResultPage').then((m) => ({ default: m.VaultResultPage }))
);
const SponsorPortalPage = lazy(() =>
  import('./sponsor/SponsorPortalPage').then((m) => ({ default: m.SponsorPortalPage }))
);
const SponsorCreatePage = lazy(() =>
  import('./sponsor/SponsorCreatePage').then((m) => ({ default: m.SponsorCreatePage }))
);
const SponsorDetailPage = lazy(() =>
  import('./sponsor/SponsorDetailPage').then((m) => ({ default: m.SponsorDetailPage }))
);
const ChallengesPage = lazy(() =>
  import('./pages/ChallengesPage').then((m) => ({ default: m.ChallengesPage }))
);
const ChallengeCreatePage = lazy(() =>
  import('./pages/ChallengeCreatePage').then((m) => ({ default: m.ChallengeCreatePage }))
);
const ChallengeDetailPage = lazy(() =>
  import('./pages/ChallengeDetailPage').then((m) => ({ default: m.ChallengeDetailPage }))
);
const AdminPage = lazy(() =>
  import('./pages/AdminPage').then((m) => ({ default: m.AdminPage }))
);
const NotFoundPage = lazy(() =>
  import('./pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage }))
);

const RouteSuspenseFallback: React.FC = () => (
  <PageContainer maxWidth="md" className="py-16">
    <LoadingState message="INITIALIZING ARCADE MODULE..." subtext="Streaming module bytecode" />
  </PageContainer>
);

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<ArcadeShell />}>
          {/* Home — Eagerly loaded for instantaneous landing experience */}
          <Route path="/" element={<HomePage />} />

          {/* Bluff or Bust — Lazy Loaded */}
          <Route
            path="/bluff"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <BluffLobbyPage />
              </Suspense>
            }
          />
          <Route
            path="/bluff/:id"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <BluffMatchPage />
              </Suspense>
            }
          />
          <Route
            path="/bluff/:id/result"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <BluffResultPage />
              </Suspense>
            }
          />

          {/* Monad Vault — Lazy Loaded */}
          <Route
            path="/vault"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <VaultSetupPage />
              </Suspense>
            }
          />
          <Route
            path="/vault/:id"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <VaultBattlePage />
              </Suspense>
            }
          />
          <Route
            path="/vault/:id/result"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <VaultResultPage />
              </Suspense>
            }
          />

          {/* Sponsor Portal — Lazy Loaded */}
          <Route
            path="/sponsor"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <SponsorPortalPage />
              </Suspense>
            }
          />
          <Route
            path="/sponsor/create"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <SponsorCreatePage />
              </Suspense>
            }
          />
          <Route
            path="/sponsor/:id"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <SponsorDetailPage />
              </Suspense>
            }
          />

          {/* Arcade Challenges & Bounties — Lazy Loaded */}
          <Route
            path="/challenges"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <ChallengesPage />
              </Suspense>
            }
          />
          <Route
            path="/challenges/create"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <ChallengeCreatePage />
              </Suspense>
            }
          />
          <Route
            path="/challenges/:id"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <ChallengeDetailPage />
              </Suspense>
            }
          />

          {/* Admin — Lazy Loaded */}
          <Route
            path="/admin"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <AdminPage />
              </Suspense>
            }
          />

          {/* 404 Fallback */}
          <Route
            path="*"
            element={
              <Suspense fallback={<RouteSuspenseFallback />}>
                <NotFoundPage />
              </Suspense>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};
