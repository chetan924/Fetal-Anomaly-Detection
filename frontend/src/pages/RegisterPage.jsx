import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  UserPlus,
  Mail,
  Lock,
  User,
  ArrowLeft,
  CheckCircle2,
} from 'lucide-react';

import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

import {
  register,
  getApiErrorMessage,
} from '../services/api';


// ============================================================
// REGISTER PAGE
// ============================================================

function RegisterPage() {
  const navigate = useNavigate();

  // ==========================================================
  // FORM STATE
  // ==========================================================

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] =
    useState('');

  // ==========================================================
  // UI STATE
  // ==========================================================

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');


  // ==========================================================
  // REGISTER
  // ==========================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError('');
    setSuccess('');

    // --------------------------------------------------------
    // NORMALIZE INPUT
    // --------------------------------------------------------

    const normalizedName =
      fullName.trim();

    const normalizedEmail =
      email.trim().toLowerCase();


    // --------------------------------------------------------
    // VALIDATION
    // --------------------------------------------------------

    if (!normalizedName) {
      setError(
        'Please enter your full name.'
      );
      return;
    }

    if (normalizedName.length < 2) {
      setError(
        'Full name must be at least 2 characters.'
      );
      return;
    }

    if (!normalizedEmail) {
      setError(
        'Please enter your email address.'
      );
      return;
    }

    if (!password) {
      setError(
        'Please enter a password.'
      );
      return;
    }

    if (password.length < 8) {
      setError(
        'Password must be at least 8 characters.'
      );
      return;
    }

    if (password.length > 128) {
      setError(
        'Password cannot be longer than 128 characters.'
      );
      return;
    }

    if (!confirmPassword) {
      setError(
        'Please confirm your password.'
      );
      return;
    }

    if (password !== confirmPassword) {
      setError(
        'Passwords do not match.'
      );
      return;
    }


    // --------------------------------------------------------
    // START REQUEST
    // --------------------------------------------------------

    setLoading(true);

    try {

      const result = await register(
        normalizedName,
        normalizedEmail,
        password
      );

      console.log(
        'Registration successful:',
        result
      );


      // ------------------------------------------------------
      // SUCCESS
      // ------------------------------------------------------

      setSuccess(
        'Account created successfully. Redirecting to sign in...'
      );


      // ------------------------------------------------------
      // REDIRECT
      // ------------------------------------------------------

      setTimeout(() => {

        navigate(
          '/login',
          {
            replace: true,
            state: {
              registered: true,
              email: normalizedEmail,
            },
          }
        );

      }, 1200);


    } catch (err) {

      console.error(
        'Registration error:',
        err
      );

      setError(
        getApiErrorMessage(
          err,
          'Registration failed. Please try again.'
        )
      );

    } finally {

      setLoading(false);

    }
  };


  // ==========================================================
  // UI
  // ==========================================================

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center px-4 py-8">

      <Card className="w-full max-w-md">

        <div className="p-6">

          {/* ==================================================
              BACK TO LOGIN
          ================================================== */}

          <div className="mb-5">

            <Link
              to="/login"
              className="inline-flex items-center text-sm font-medium text-slate-500 transition hover:text-teal-600"
            >

              <ArrowLeft
                size={16}
                className="mr-2"
              />

              Back to sign in

            </Link>

          </div>


          {/* ==================================================
              HEADER
          ================================================== */}

          <div className="mb-6 text-center">

            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-teal-50">

              <UserPlus
                size={24}
                className="text-teal-600"
              />

            </div>


            <h1 className="text-2xl font-semibold text-slate-900">
              Create your account
            </h1>


            <p className="mt-2 text-sm text-slate-500">
              Create your FetalAI clinical account.
            </p>

          </div>


          {/* ==================================================
              REGISTER FORM
          ================================================== */}

          <form
            onSubmit={handleSubmit}
            className="space-y-5"
          >

            {/* =================================================
                FULL NAME
            ================================================= */}

            <div>

              <label
                htmlFor="fullName"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Full name
              </label>


              <div className="relative">

                <User
                  size={18}
                  className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                />


                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  value={fullName}
                  onChange={(event) =>
                    setFullName(
                      event.target.value
                    )
                  }
                  placeholder="Dr. John Doe"
                  required
                  minLength={2}
                  maxLength={120}
                  autoComplete="name"
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />

              </div>

            </div>


            {/* =================================================
                EMAIL
            ================================================= */}

            <div>

              <label
                htmlFor="email"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Email
              </label>


              <div className="relative">

                <Mail
                  size={18}
                  className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                />


                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(
                      event.target.value
                    )
                  }
                  placeholder="doctor@example.com"
                  required
                  autoComplete="email"
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />

              </div>

            </div>


            {/* =================================================
                PASSWORD
            ================================================= */}

            <div>

              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Password
              </label>


              <div className="relative">

                <Lock
                  size={18}
                  className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                />


                <input
                  id="password"
                  name="password"
                  type="password"
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.target.value
                    )
                  }
                  placeholder="Minimum 8 characters"
                  required
                  minLength={8}
                  maxLength={128}
                  autoComplete="new-password"
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />

              </div>


              <p className="mt-2 text-xs text-slate-400">
                Use at least 8 characters.
              </p>

            </div>


            {/* =================================================
                CONFIRM PASSWORD
            ================================================= */}

            <div>

              <label
                htmlFor="confirmPassword"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Confirm password
              </label>


              <div className="relative">

                <Lock
                  size={18}
                  className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                />


                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(
                      event.target.value
                    )
                  }
                  placeholder="Re-enter your password"
                  required
                  minLength={8}
                  maxLength={128}
                  autoComplete="new-password"
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />

              </div>

            </div>


            {/* =================================================
                PASSWORD MATCH
            ================================================= */}

            {confirmPassword &&
              password === confirmPassword && (
                <div className="flex items-center text-xs text-emerald-600">

                  <CheckCircle2
                    size={15}
                    className="mr-2"
                  />

                  Passwords match.

                </div>
              )}


            {/* =================================================
                PASSWORD MISMATCH
            ================================================= */}

            {confirmPassword &&
              password !== confirmPassword && (
                <div className="text-xs text-rose-600">
                  Passwords do not match.
                </div>
              )}


            {/* =================================================
                ERROR
            ================================================= */}

            {error && (
              <div
                role="alert"
                aria-live="polite"
                className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
              >
                {error}
              </div>
            )}


            {/* =================================================
                SUCCESS
            ================================================= */}

            {success && (
              <div
                role="status"
                aria-live="polite"
                className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
              >
                {success}
              </div>
            )}


            {/* =================================================
                CREATE ACCOUNT
            ================================================= */}

            <Button
              type="submit"
              disabled={
                loading ||
                !fullName.trim() ||
                !email.trim() ||
                !password ||
                !confirmPassword
              }
              className="w-full"
            >

              <UserPlus
                size={18}
                className="mr-2"
              />


              {loading
                ? 'Creating account...'
                : 'Create account'}

            </Button>

          </form>


          {/* ==================================================
              LOGIN LINK
          ================================================== */}

          <div className="mt-6 text-center">

            <p className="text-sm text-slate-500">

              Already have an account?{' '}

              <Link
                to="/login"
                className="font-medium text-teal-600 transition hover:text-teal-700"
              >
                Sign in
              </Link>

            </p>

          </div>


          {/* ==================================================
              FOOTER
          ================================================== */}

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


export default RegisterPage;