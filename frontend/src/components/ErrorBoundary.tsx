import { Component, ErrorInfo, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, RefreshCw, ArrowLeft } from 'lucide-react';
import { PageContainer } from './PageContainer';
import { Panel } from './Panel';
import { ArcadeButton } from './ArcadeButton';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Robust React Error Boundary for Mon Arcade.
 * Traps runtime rendering exceptions and state transition anomalies,
 * guaranteeing the interface NEVER turns into a blank/black screen.
 */
export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary intercepted unhandled render error:', error, errorInfo);
  }

  public handleReload = () => {
    window.location.reload();
  };

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <PageContainer maxWidth="md" className="py-12 space-y-6">
          <Panel header="ARCADE SYSTEM RECOVERY" accent="danger">
            <div className="py-6 text-center space-y-4">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-arcade-danger/10 border border-arcade-danger/40 text-arcade-danger">
                <AlertCircle className="w-7 h-7" />
              </div>

              <div className="space-y-1">
                <h2 className="font-display text-lg text-arcade-text tracking-wide uppercase">
                  DUEL INTERACTION HIT AN UNEXPECTED STATE
                </h2>
                <p className="text-xs font-mono text-arcade-danger max-w-md mx-auto">
                  {this.state.error?.message || 'An unexpected rendering error occurred.'}
                </p>
                <p className="text-[11px] font-mono text-arcade-subtle mt-1">
                  Authoritative match state is safely preserved on the server.
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-3 pt-3">
                <ArcadeButton variant="secondary" size="md" onClick={this.handleReload}>
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                  RELOAD ARENA
                </ArcadeButton>
                <Link to="/bluff" onClick={this.handleReset}>
                  <ArcadeButton variant="pink" size="md">
                    <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
                    RETURN TO LOBBY
                  </ArcadeButton>
                </Link>
              </div>
            </div>
          </Panel>
        </PageContainer>
      );
    }

    return this.props.children;
  }
}
