import React from 'react';
import { PageContainer } from '../components/PageContainer';
import { Panel } from '../components/Panel';
import { StatBar } from '../components/StatBar';
import { Activity, Database, Cpu } from 'lucide-react';

export const AdminPage: React.FC = () => {
  return (
    <PageContainer maxWidth="lg" className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-arcade-border">
        <div>
          <h1 className="font-display text-xl text-arcade-text tracking-wider">
            ARCADE ADMIN CONSOLE
          </h1>
          <p className="text-xs font-mono text-arcade-muted mt-0.5">
            SYSTEM TELEMETRY & ADAPTER HEALTH
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 rounded bg-arcade-panel border border-arcade-border text-xs font-mono text-arcade-lime">
          <Activity className="w-3.5 h-3.5" />
          <span>ALL ADAPTERS HEALTHY</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Panel header="BLOCKCHAIN ADAPTER">
          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center gap-2 text-arcade-lime">
              <Cpu className="w-4 h-4" />
              <span className="font-bold">MockBlockchain (Active)</span>
            </div>
            <p className="text-arcade-muted">
              Simulation mode enabled. Monad RPC connection isolated behind seam.
            </p>
          </div>
        </Panel>

        <Panel header="AI AGENT PROVIDER">
          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center gap-2 text-arcade-cyan">
              <Cpu className="w-4 h-4" />
              <span className="font-bold">MockAgentProvider (Active)</span>
            </div>
            <p className="text-arcade-muted">
              Warden and Attacker agents responding deterministically for fast tests.
            </p>
          </div>
        </Panel>

        <Panel header="DATABASE HEALTH">
          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center gap-2 text-arcade-text">
              <Database className="w-4 h-4" />
              <span className="font-bold">PostgreSQL / AsyncPG</span>
            </div>
            <p className="text-arcade-muted">
              Connection pool configured via DATABASE_URL.
            </p>
          </div>
        </Panel>
      </div>

      <Panel header="SYSTEM RESOURCE USAGE">
        <div className="space-y-4 max-w-xl">
          <StatBar label="Memory Capacity" value={34} max={100} color="lime" showPercentage />
          <StatBar label="Transaction Queue Depth" value={2} max={100} color="cyan" showPercentage />
        </div>
      </Panel>
    </PageContainer>
  );
};
