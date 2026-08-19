import { Routes, Route, Navigate } from 'react-router-dom';

import Layout from './components/layout/Layout';

// ============================================================
// PUBLIC PAGES
// ============================================================

import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
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
  const token = localStorage.getItem(
    'access_token'
  );

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
// PUBLIC ROUTE
// ============================================================

function PublicRoute({ children }) {
  const token = localStorage.getItem(
    'access_token'
  );

  /*
   * If the user is already logged in,
   * don't allow them to stay on login/register pages.
   */

  if (token) {
    return (
      <Navigate
        to="/"
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
          PUBLIC AUTHENTICATION ROUTES
      ====================================================== */}

      {/* ====================================================
          LOGIN
      ==================================================== */}

      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />


      {/* ====================================================
          REGISTER
      ==================================================== */}

      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />


      {/* ====================================================
          FORGOT PASSWORD
      ==================================================== */}

      <Route
        path="/forgot-password"
        element={
          <PublicRoute>
            <ForgotPasswordPage />
          </PublicRoute>
        }
      />


      {/* ====================================================
          RESET PASSWORD
      ==================================================== */}

      <Route
        path="/reset-password"
        element={
          <PublicRoute>
            <ResetPasswordPage />
          </PublicRoute>
        }
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
            SETTINGS
        ==================================================== */}

        <Route
          path="settings"
          element={<SettingsPage />}
        />


        {/* ====================================================
            HELP
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