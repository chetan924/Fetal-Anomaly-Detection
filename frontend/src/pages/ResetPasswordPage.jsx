import { useMemo, useState } from 'react';
import {
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  LockKeyhole,
  ArrowLeft,
} from 'lucide-react';
import {
  Link,
  useNavigate,
  useSearchParams,
} from 'react-router-dom';

import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { resetPassword } from '../services/api';


function ResetPasswordPage() {
  const navigate = useNavigate();

  const [searchParams] = useSearchParams();

  const token = useMemo(
    () => searchParams.get('token') || '',
    [searchParams]
  );

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] =
    useState('');

  const [showPassword, setShowPassword] =
    useState(false);

  const [showConfirmPassword, setShowConfirmPassword] =
    useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);


  // ============================================================
  // PASSWORD VALIDATION
  // ============================================================

  const passwordLengthValid =
    password.length >= 8;

  const passwordsMatch =
    password.length > 0 &&
    password === confirmPassword;


  // ============================================================
  // SUBMIT
  // ============================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError('');

    // ----------------------------------------------------------
    // TOKEN
    // ----------------------------------------------------------

    if (!token) {
      setError(
        'This password reset link is invalid or incomplete.'
      );

      return;
    }


    // ----------------------------------------------------------
    // PASSWORD
    // ----------------------------------------------------------

    if (!passwordLengthValid) {
      setError(
        'Password must contain at least 8 characters.'
      );

      return;
    }


    if (!passwordsMatch) {
      setError(
        'Passwords do not match.'
      );

      return;
    }


    setLoading(true);


    try {
      await resetPassword(
        token,
        password
      );

      setSuccess(true);

    } catch (err) {
      console.error(
        'Password reset error:',
        err
      );

      const detail =
        err.response?.data?.detail;

      let message =
        'Unable to reset your password. Please try again.';

      if (Array.isArray(detail)) {
        message = detail
          .map((item) => item.msg)
          .join(', ');
      } else if (detail) {
        message = detail;
      } else if (err.message) {
        message = err.message;
      }

      setError(message);

    } finally {
      setLoading(false);
    }
  };


  // ============================================================
  // SUCCESS VIEW
  // ============================================================

  if (success) {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-10">

        <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-md items-center justify-center">

          <Card className="w-full p-8">

            <div className="text-center">

              <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">

                <CheckCircle2
                  size={34}
                  className="text-emerald-600"
                />

              </div>


              <h1 className="text-2xl font-bold text-slate-900">
                Password reset successful
              </h1>


              <p className="mt-3 text-sm leading-6 text-slate-600">
                Your password has been changed successfully.
                You can now sign in with your new password.
              </p>


              <Button
                type="button"
                className="mt-6 w-full"
                onClick={() =>
                  navigate('/login', {
                    replace: true,
                  })
                }
              >
                Back to sign in
              </Button>

            </div>

          </Card>

        </div>

      </main>
    );
  }


  // ============================================================
  // INVALID TOKEN VIEW
  // ============================================================

  if (!token) {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-10">

        <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-md items-center justify-center">

          <Card className="w-full p-8">

            <div className="text-center">

              <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-rose-100">

                <KeyRound
                  size={32}
                  className="text-rose-600"
                />

              </div>


              <h1 className="text-2xl font-bold text-slate-900">
                Invalid reset link
              </h1>


              <p className="mt-3 text-sm leading-6 text-slate-600">
                This password reset link is missing or invalid.
                Please request a new password reset link.
              </p>


              <Link
                to="/forgot-password"
                className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-teal-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-teal-700"
              >
                Request a new reset link
              </Link>

            </div>

          </Card>

        </div>

      </main>
    );
  }


  // ============================================================
  // RESET FORM
  // ============================================================

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10">

      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-md items-center justify-center">

        <Card className="w-full p-8">

          {/* ================================================== */}
          {/* HEADER */}
          {/* ================================================== */}

          <div className="mb-8">

            <Link
              to="/login"
              className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-900"
            >
              <ArrowLeft size={16} />

              Back to sign in
            </Link>


            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-teal-600/10">

              <LockKeyhole
                size={24}
                className="text-teal-600"
              />

            </div>


            <h1 className="text-2xl font-bold text-slate-900">
              Create a new password
            </h1>


            <p className="mt-2 text-sm leading-6 text-slate-600">
              Choose a strong password for your FetalAI
              account.
            </p>

          </div>


          {/* ================================================== */}
          {/* FORM */}
          {/* ================================================== */}

          <form
            onSubmit={handleSubmit}
            className="space-y-5"
          >

            {/* ================================================= */}
            {/* NEW PASSWORD */}
            {/* ================================================= */}

            <div>

              <label
                htmlFor="new-password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                New password
              </label>


              <div className="relative">

                <input
                  id="new-password"
                  type={
                    showPassword
                      ? 'text'
                      : 'password'
                  }
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.target.value
                    )
                  }
                  placeholder="Enter new password"
                  autoComplete="new-password"
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pr-12 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />


                <button
                  type="button"
                  onClick={() =>
                    setShowPassword(
                      (value) => !value
                    )
                  }
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 transition hover:text-slate-700"
                  aria-label={
                    showPassword
                      ? 'Hide password'
                      : 'Show password'
                  }
                >

                  {showPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}

                </button>

              </div>


              <p
                className={`mt-2 text-xs ${
                  passwordLengthValid
                    ? 'text-emerald-600'
                    : 'text-slate-500'
                }`}
              >
                {passwordLengthValid
                  ? '✓ Password length is valid'
                  : 'Use at least 8 characters'}
              </p>

            </div>


            {/* ================================================= */}
            {/* CONFIRM PASSWORD */}
            {/* ================================================= */}

            <div>

              <label
                htmlFor="confirm-password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Confirm new password
              </label>


              <div className="relative">

                <input
                  id="confirm-password"
                  type={
                    showConfirmPassword
                      ? 'text'
                      : 'password'
                  }
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(
                      event.target.value
                    )
                  }
                  placeholder="Confirm new password"
                  autoComplete="new-password"
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pr-12 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />


                <button
                  type="button"
                  onClick={() =>
                    setShowConfirmPassword(
                      (value) => !value
                    )
                  }
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 transition hover:text-slate-700"
                  aria-label={
                    showConfirmPassword
                      ? 'Hide confirm password'
                      : 'Show confirm password'
                  }
                >

                  {showConfirmPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}

                </button>

              </div>


              {confirmPassword && (
                <p
                  className={`mt-2 text-xs ${
                    passwordsMatch
                      ? 'text-emerald-600'
                      : 'text-rose-600'
                  }`}
                >
                  {passwordsMatch
                    ? '✓ Passwords match'
                    : 'Passwords do not match'}
                </p>
              )}

            </div>


            {/* ================================================= */}
            {/* ERROR */}
            {/* ================================================= */}

            {error && (
              <div
                role="alert"
                className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-5 text-rose-700"
              >
                {error}
              </div>
            )}


            {/* ================================================= */}
            {/* SECURITY INFO */}
            {/* ================================================= */}

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

              <div className="flex gap-3">

                <KeyRound
                  size={19}
                  className="mt-0.5 shrink-0 text-teal-600"
                />

                <div>

                  <p className="text-sm font-medium text-slate-700">
                    Secure password reset
                  </p>

                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    Your reset link can only be used once and
                    expires after a limited time.
                  </p>

                </div>

              </div>

            </div>


            {/* ================================================= */}
            {/* SUBMIT */}
            {/* ================================================= */}

            <Button
              type="submit"
              disabled={
                loading ||
                !password ||
                !confirmPassword
              }
              className="w-full"
            >

              <LockKeyhole
                size={18}
                className="mr-2"
              />

              {loading
                ? 'Resetting password...'
                : 'Reset password'}

            </Button>

          </form>

        </Card>

      </div>

    </main>
  );
}


export default ResetPasswordPage;