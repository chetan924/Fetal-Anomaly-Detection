import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LogIn, UserPlus } from 'lucide-react';

import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

import { login } from '../services/api';

function LoginPage() {
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ============================================================
  // ERROR MESSAGE
  // ============================================================

  const getErrorMessage = (err) => {
    const detail = err?.response?.data?.detail;

    if (typeof detail === 'string') {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === 'string') {
            return item;
          }

          if (item?.msg) {
            return item.msg;
          }

          return 'Invalid request.';
        })
        .join(', ');
    }

    if (typeof err?.message === 'string') {
      return err.message;
    }

    return 'Login failed. Please check your credentials.';
  };

  // ============================================================
  // LOGIN
  // ============================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError('');

    const normalizedEmail = email.trim();

    if (!normalizedEmail) {
      setError('Please enter your email address.');
      return;
    }

    if (!password) {
      setError('Please enter your password.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);

    try {
      const result = await login(
        normalizedEmail,
        password
      );

      if (!result?.access_token) {
        throw new Error(
          'No access token received from server.'
        );
      }

      localStorage.setItem(
        'access_token',
        result.access_token
      );

      const savedToken =
        localStorage.getItem('access_token');

      if (!savedToken) {
        throw new Error(
          'Authentication token could not be saved.'
        );
      }

      navigate('/', {
        replace: true,
      });

    } catch (err) {
      console.error(
        'Login error:',
        err
      );

      setError(
        getErrorMessage(err)
      );

    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // UI
  // ============================================================

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center px-4">

      <Card className="w-full max-w-md">

        <div className="p-6">

          {/* ================================================== */}
          {/* HEADER */}
          {/* ================================================== */}

          <div className="mb-6 text-center">

            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-teal-50">

              <LogIn
                size={24}
                className="text-teal-600"
              />

            </div>

            <h1 className="text-2xl font-semibold text-slate-900">
              Sign in
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Sign in to access the Fetal Anomaly Detection system.
            </p>

          </div>

          {/* ================================================== */}
          {/* LOGIN FORM */}
          {/* ================================================== */}

          <form
            onSubmit={handleSubmit}
            className="space-y-5"
          >

            {/* EMAIL */}

            <div>

              <label
                htmlFor="email"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Email
              </label>

              <input
                id="email"
                name="email"
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                placeholder="doctor@example.com"
                required
                autoComplete="email"
                disabled={loading}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
              />

            </div>

            {/* PASSWORD */}

            <div>

              <div className="mb-2 flex items-center justify-between">

                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-slate-700"
                >
                  Password
                </label>

                <Link
                  to="/forgot-password"
                  className="text-sm font-medium text-teal-600 transition hover:text-teal-700"
                >
                  Forgot password?
                </Link>

              </div>

              <input
                id="password"
                name="password"
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Enter your password"
                required
                minLength={8}
                autoComplete="current-password"
                disabled={loading}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
              />

            </div>

            {/* ERROR */}

            {error && (
              <div
                role="alert"
                aria-live="polite"
                className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
              >
                {error}
              </div>
            )}

            {/* SIGN IN BUTTON */}

            <Button
              type="submit"
              disabled={
                loading ||
                !email.trim() ||
                !password
              }
              className="w-full"
            >

              <LogIn
                size={18}
                className="mr-2"
              />

              {loading
                ? 'Signing in...'
                : 'Sign in'}

            </Button>

          </form>

          {/* ================================================== */}
          {/* SIGN UP */}
          {/* ================================================== */}

          <div className="mt-6">

            <div className="relative">

              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200" />
              </div>

              <div className="relative flex justify-center">
                <span className="bg-white px-3 text-xs text-slate-400">
                  New to FetalAI?
                </span>
              </div>

            </div>

            <Link
              to="/register"
              className="mt-4 flex w-full items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-teal-400 hover:bg-teal-50 hover:text-teal-700"
            >

              <UserPlus
                size={18}
                className="mr-2"
              />

              Create an account

            </Link>

          </div>

          {/* ================================================== */}
          {/* FOOTER */}
          {/* ================================================== */}

          <div className="mt-6 text-center">

            <p className="text-xs text-slate-400">
              FetalAI Clinical AI Platform
            </p>

          </div>

        </div>

      </Card>

    </main>
  );
}

export default LoginPage;