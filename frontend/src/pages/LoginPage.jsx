import { useState } from 'react';
import {
  Link,
  useNavigate,
} from 'react-router-dom';

import { LogIn } from 'lucide-react';

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
  // LOGIN
  // ============================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError('');
    setLoading(true);

    try {
      // --------------------------------------------------------
      // LOGIN API
      // --------------------------------------------------------

      const result = await login(
        email.trim(),
        password
      );


      // --------------------------------------------------------
      // VALIDATE TOKEN
      // --------------------------------------------------------

      if (!result?.access_token) {
        throw new Error(
          'No access token received from server.'
        );
      }


      // --------------------------------------------------------
      // SAVE JWT TOKEN
      // --------------------------------------------------------

      localStorage.setItem(
        'access_token',
        result.access_token
      );


      // --------------------------------------------------------
      // VERIFY TOKEN WAS SAVED
      // --------------------------------------------------------

      const savedToken =
        localStorage.getItem(
          'access_token'
        );

      if (!savedToken) {
        throw new Error(
          'Authentication token could not be saved.'
        );
      }


      // --------------------------------------------------------
      // LOGIN SUCCESS
      // --------------------------------------------------------

      navigate('/', {
        replace: true,
      });

    } catch (err) {
      console.error(
        'Login error:',
        err
      );

      const message =
        err.response?.data?.detail ||
        err.message ||
        'Login failed. Please check your credentials.';

      setError(message);

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

            {/* ================================================= */}
            {/* EMAIL */}
            {/* ================================================= */}

            <div>

              <label
                htmlFor="email"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Email
              </label>


              <input
                id="email"
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


            {/* ================================================= */}
            {/* PASSWORD */}
            {/* ================================================= */}

            <div>

              <div className="mb-2 flex items-center justify-between">

                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-slate-700"
                >
                  Password
                </label>


                {/* FORGOT PASSWORD */}

                <Link
                  to="/forgot-password"
                  className="text-sm font-medium text-teal-600 transition hover:text-teal-700"
                >
                  Forgot password?
                </Link>

              </div>


              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Enter your password"
                required
                autoComplete="current-password"
                disabled={loading}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
              />

            </div>


            {/* ================================================= */}
            {/* ERROR */}
            {/* ================================================= */}

            {error && (
              <div
                role="alert"
                className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
              >
                {error}
              </div>
            )}


            {/* ================================================= */}
            {/* SUBMIT */}
            {/* ================================================= */}

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