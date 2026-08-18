import { Routes, Route, Navigate } from 'react-router-dom';

import Layout from './components/layout/Layout';

// ============================================================
// PUBLIC PAGES
// ============================================================

import LoginPage from './pages/LoginPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';

// ============================================================
// APPLICATION PAGES
// ============================================================

import DashboardPage from './pages/DashboardPage';
import NewScanPage from './pages/NewScanPage';
import PatientsPage from './pages/PatientsPage';
import ScanHistoryPage from './pages/ScanHistoryPage';
import ReportsPage from './pages/ReportsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import NotificationsPage from './pages/NotificationsPage';
import SettingsPage from './pages/SettingsPage';
import HelpPage from './pages/HelpPage';


// ============================================================
// PROTECTED ROUTE
// ============================================================

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('access_token');

  if (!token) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return children;
}


// ============================================================
// APP
// ============================================================

function App() {
  return (
    <Routes>

      {/* ======================================================
          PUBLIC ROUTES
      ====================================================== */}

      {/* Login */}

      <Route
        path="/login"
        element={<LoginPage />}
      />


      {/* Forgot Password */}

      <Route
        path="/forgot-password"
        element={<ForgotPasswordPage />}
      />


      {/* Reset Password */}

      <Route
        path="/reset-password"
        element={<ResetPasswordPage />}
      />


      {/* ======================================================
          PROTECTED APPLICATION
      ====================================================== */}

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >

        {/* ====================================================
            DEFAULT DASHBOARD
        ==================================================== */}

        <Route
          index
          element={<DashboardPage />}
        />


        {/* ====================================================
            DASHBOARD
        ==================================================== */}

        <Route
          path="dashboard"
          element={<DashboardPage />}
        />


        {/* ====================================================
            NEW SCAN
        ==================================================== */}

        <Route
          path="new-scan"
          element={<NewScanPage />}
        />


        {/* ====================================================
            PATIENTS
        ==================================================== */}

        <Route
          path="patients"
          element={<PatientsPage />}
        />


        {/* ====================================================
            SCAN HISTORY
        ==================================================== */}

        <Route
          path="scan-history"
          element={<ScanHistoryPage />}
        />


        {/* ====================================================
            REPORTS
        ==================================================== */}

        <Route
          path="reports"
          element={<ReportsPage />}
        />


        {/* ====================================================
            ANALYTICS
        ==================================================== */}

        <Route
          path="analytics"
          element={<AnalyticsPage />}
        />


        {/* ====================================================
            NOTIFICATIONS
        ==================================================== */}

        <Route
          path="notifications"
          element={<NotificationsPage />}
        />


        {/* ====================================================
            SETTINGS / DOCTOR PROFILE
        ==================================================== */}

        <Route
          path="settings"
          element={<SettingsPage />}
        />


        {/* ====================================================
            HELP & SUPPORT
        ==================================================== */}

        <Route
          path="help"
          element={<HelpPage />}
        />

      </Route>


      {/* ======================================================
          UNKNOWN ROUTE
      ====================================================== */}

      <Route
        path="*"
        element={
          <Navigate
            to="/"
            replace
          />
        }
      />

    </Routes>
  );
}


export default App;