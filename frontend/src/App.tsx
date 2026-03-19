import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '@/components/Layout/Layout'
import { DashboardPage } from '@/pages/Dashboard'
import { TransactionsPage } from '@/pages/Transactions'
import { SplitBillsPage } from '@/pages/SplitBills'
import { BudgetPage } from '@/pages/Budget'
import { GoalsPage } from '@/pages/Goals'
import { DebtsPage } from '@/pages/Debts'
import { SubscriptionsPage } from '@/pages/Subscriptions'
import { ReportsPage } from '@/pages/Reports'
import { SettingsPage } from '@/pages/Settings'
import { EmailParsersPage } from '@/pages/Settings/EmailParsers'
import { ParserGeneratorPage } from '@/pages/Settings/ParserGenerator'
import { SyncPage } from '@/pages/Settings/SyncPage'
import { BackupPage } from '@/pages/Settings/BackupPage'
import { ExportPage } from '@/pages/Settings/ExportPage'
import { OnboardingPage } from '@/pages/Onboarding'

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            <Layout>
              <DashboardPage />
            </Layout>
          }
        />
        <Route
          path="/transactions"
          element={
            <Layout>
              <TransactionsPage />
            </Layout>
          }
        />
        <Route
          path="/split-bills"
          element={
            <Layout>
              <SplitBillsPage />
            </Layout>
          }
        />
        <Route
          path="/budget"
          element={
            <Layout>
              <BudgetPage />
            </Layout>
          }
        />
        <Route
          path="/goals"
          element={
            <Layout>
              <GoalsPage />
            </Layout>
          }
        />
        <Route
          path="/debts"
          element={
            <Layout>
              <DebtsPage />
            </Layout>
          }
        />
        <Route
          path="/subscriptions"
          element={
            <Layout>
              <SubscriptionsPage />
            </Layout>
          }
        />
        <Route
          path="/reports"
          element={
            <Layout>
              <ReportsPage />
            </Layout>
          }
        />
        <Route
          path="/settings"
          element={
            <Layout>
              <SettingsPage />
            </Layout>
          }
        />
        <Route
          path="/settings/email-parsers"
          element={
            <Layout>
              <EmailParsersPage />
            </Layout>
          }
        />
        <Route
          path="/settings/parser-generator"
          element={
            <Layout>
              <ParserGeneratorPage />
            </Layout>
          }
        />
        <Route
          path="/settings/sync"
          element={
            <Layout>
              <SyncPage />
            </Layout>
          }
        />
        <Route
          path="/settings/backup"
          element={
            <Layout>
              <BackupPage />
            </Layout>
          }
        />
        <Route
          path="/settings/export"
          element={
            <Layout>
              <ExportPage />
            </Layout>
          }
        />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
