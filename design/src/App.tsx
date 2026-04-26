/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Suspense, lazy, type ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { AppProvider } from "./store/AppContext";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Portfolio = lazy(() => import("./pages/Portfolio"));
const ContentExplorer = lazy(() => import("./pages/ContentExplorer"));
const CalendarPlanner = lazy(() => import("./pages/CalendarPlanner"));
const ChannelAnalytics = lazy(() => import("./pages/ChannelAnalytics"));
const ChannelManager = lazy(() => import("./pages/ChannelManager"));
const Settings = lazy(() => import("./pages/Settings"));
const Reports = lazy(() => import("./pages/Reports"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const Inbox = lazy(() => import("./pages/Inbox"));

function RouteShell({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="min-h-screen bg-obsidian-950" />}>{children}</Suspense>;
}

export default function App() {
  const basename = window.__SOCIAL_MARKETING__?.basename || "/";
  return (
    <AppProvider>
      <BrowserRouter basename={basename}>
        <RouteShell>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route path="/" element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route index element={<Dashboard />} />
                <Route path="portfolio" element={<Portfolio />} />
                <Route path="channels" element={<ChannelAnalytics />} />
                <Route path="content" element={<ContentExplorer />} />
                <Route path="calendar" element={<CalendarPlanner />} />
                <Route path="manage" element={<ChannelManager />} />
                <Route path="inbox" element={<Inbox />} />
                <Route path="reports" element={<Reports />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </RouteShell>
      </BrowserRouter>
    </AppProvider>
  );
}
