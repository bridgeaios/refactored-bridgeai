import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from './layouts/AppShell';
import { GatewayShell } from './layouts/GatewayShell';
import { ErrorBoundary } from './core/components/ErrorBoundary';

import { HomePage }         from './pages/HomePage';
import { DashboardPage }    from './pages/DashboardPage';
import { AppsPage }         from './pages/AppsPage';
import { LandingPage }      from './pages/LandingPage';
import { GatewayPage }      from './pages/GatewayPage';
import { JoinPage }         from './pages/JoinPage';

import { TreasuryPage }     from './domains/economy/TreasuryPage';
import { CfoPage }          from './domains/economy/CfoPage';
import { LendingPage }      from './domains/economy/LendingPage';
import { StakingPage }      from './domains/economy/StakingPage';
import { DexPage }          from './domains/economy/DexPage';

import { AgentsPage }       from './domains/twins/AgentsPage';
import { DigitalTwinPage }  from './domains/twins/DigitalTwinPage';

import { NetworkDashboardPage } from './domains/network/NetworkDashboardPage';
import { BanPage }          from './domains/network/BanPage';
import { StatusPage }       from './domains/network/StatusPage';

import { ControlPlanePage } from './domains/governance/ControlPlanePage';

import { SettingsPage }     from './domains/infra/SettingsPage';
import { DocsPage }         from './domains/infra/DocsPage';

import './index.css';
import './core/theme/tokens.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary domain="App">
        <Routes>
          <Route element={<GatewayShell />}>
            <Route path="/gateway"  element={<GatewayPage />} />
            <Route path="/join"     element={<JoinPage />} />
            <Route path="/landing"  element={<LandingPage />} />
          </Route>

          <Route element={<AppShell />}>
            <Route path="/"          element={<HomePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/apps"      element={<AppsPage />} />

            <Route path="/treasury"  element={<TreasuryPage />} />
            <Route path="/cfo"       element={<CfoPage />} />
            <Route path="/lending"   element={<LendingPage />} />
            <Route path="/staking"   element={<StakingPage />} />
            <Route path="/dex"       element={<DexPage />} />

            <Route path="/twin"      element={<DigitalTwinPage />} />
            <Route path="/agents"    element={<AgentsPage />} />

            <Route path="/network"   element={<NetworkDashboardPage />} />
            <Route path="/ban"       element={<BanPage />} />
            <Route path="/status"    element={<StatusPage />} />

            <Route path="/control"   element={<ControlPlanePage />} />

            <Route path="/settings"  element={<SettingsPage />} />
            <Route path="/docs"      element={<DocsPage />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
