import React from 'react';
import { Link } from 'react-router-dom';
import { PageContainer } from '../components/PageContainer';
import { Panel } from '../components/Panel';
import { ArcadeButton } from '../components/ArcadeButton';
import { HelpCircle, ArrowLeft } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <PageContainer maxWidth="md" className="space-y-6 text-center py-12">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-arcade-danger/10 border border-arcade-danger/40 text-arcade-danger mb-2">
        <HelpCircle className="w-8 h-8" />
      </div>

      <h1 className="font-display text-2xl sm:text-3xl text-arcade-danger tracking-wider uppercase">
        404 &bull; CABINET NOT FOUND
      </h1>

      <p className="text-arcade-muted text-sm max-w-md mx-auto font-sans">
        The machine or match route you requested does not exist in the Mon Arcade matrix.
      </p>

      <Panel className="max-w-sm mx-auto text-xs font-mono text-arcade-subtle">
        <span>ERROR CODE: ERR_ARCADE_ROUTE_UNDEFINED</span>
      </Panel>

      <div className="pt-4">
        <Link to="/">
          <ArcadeButton variant="secondary" size="md">
            <ArrowLeft className="w-3.5 h-3.5 mr-2" />
            RETURN TO LOBBY
          </ArcadeButton>
        </Link>
      </div>
    </PageContainer>
  );
};
