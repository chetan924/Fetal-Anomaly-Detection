import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  UserPlus,
  Mail,
  Lock,
  User,
  ArrowLeft,
  CheckCircle2,
  ShieldCheck,
  RefreshCw,
  KeyRound,
} from 'lucide-react';

import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

import {
  register,
  verifySignupOTP,
  resendSignupOTP,
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
  const [otp, setOtp] = useState('');

  // ==========================================================
  // UI STATE
  // ==========================================================

  const [step, setStep] = useState('form'); // 'form' | 'otp'
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // ==========================================================
  // COOLDOWN TIMER
  // ==========================================================

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);


  // ==========================================================
  // STEP 1 — REGISTER
  // ==========================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError('');
    setSuccess('');

    const normalizedName = fullName.trim();
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedName) {
      setError('Please enter your full name.');
      return;
    }

    if (normalizedName.length < 2) {
      setError('Full name must be at least 2 characters.');
      return;
    }

    if (!normalizedEmail) {
      setError('Please enter your email address.');
      return;
    }

    if (!password) {
      setError('Please enter a password.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    if (password.length > 128) {
      setError('Password cannot be longer than 128 characters.');
      return;
    }

    if (!confirmPassword) {
      setError('Please confirm your password.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);

    try {
      const result = await register(
        normalizedName,
        normalizedEmail,
        password
      );

      setStep('otp');
      setOtp('');
      setCooldown(60);
      setSuccess(
        result?.message || 'A 6-digit verification code has been sent to your email.'
      );

    } catch (err) {
      console.error('Registration error:', err);
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
  // STEP 2 — VERIFY OTP
  // ==========================================================

  const handleVerifyOTP = async (event) => {
    event.preventDefault();

    setError('');
    setSuccess('');

    const normalizedEmail = email.trim().toLowerCase();
    const normalizedOTP = otp.trim();

    if (!normalizedOTP) {
      setError('Please enter the verification code.');
      return;
    }

    if (!/^\d{6}$/.test(normalizedOTP)) {
      setError('Please enter the 6-digit OTP.');
      return;
    }

    setLoading(true);

    try {
      await verifySignupOTP(normalizedEmail, normalizedOTP);

      setSuccess('Account verified successfully! Redirecting to sign in...');

      setTimeout(() => {
        navigate('/login', {
          replace: true,
          state: {
            registered: true,
            email: normalizedEmail,
          },
        });
      }, 1200);

    } catch (err) {
      console.error('OTP verification error:', err);
      setError(
        getApiErrorMessage(
          err,
          'Invalid or expired OTP. Please try again.'
        )
      );
    } finally {
      setLoading(false);
    }
  };


  // ==========================================================
  // RESEND OTP
  // ==========================================================

  const handleResendOTP = async () => {
    if (cooldown > 0 || resendLoading) return;

    setError('');
    setSuccess('');
    setResendLoading(true);

    try {
      const result = await resendSignupOTP(email.trim().toLowerCase());
      setCooldown(60);
      setSuccess(
        result?.message || 'A new verification code has been sent to your email.'
      );
    } catch (err) {
      console.error('Resend OTP error:', err);
      setError(
        getApiErrorMessage(
          err,
          'Failed to resend verification code. Please try again.'
        )
      );
    } finally {
      setResendLoading(false);
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

              {step === 'otp' ? (
                <ShieldCheck
                  size={24}
                  className="text-teal-600"
                />
              ) : (
                <UserPlus
                  size={24}
                  className="text-teal-600"
                />
              )}

            </div>


            <h1 className="text-2xl font-semibold text-slate-900">
              {step === 'otp'
                ? 'Verify your email'
                : 'Create your account'}
            </h1>


            <p className="mt-2 text-sm text-slate-500">
              {step === 'otp'
                ? 'Enter the 6-digit verification code sent to your email.'
                : 'Create your FetalAI clinical account.'}
            </p>

          </div>


          {/* ==================================================
              STEP 1 — REGISTER FORM
          ================================================== */}

          {step === 'form' && (

            <form
              onSubmit={handleSubmit}
              className="space-y-5"
            >

              {/* FULL NAME */}

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


              {/* EMAIL */}

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


              {/* PASSWORD */}

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


              {/* CONFIRM PASSWORD */}

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


              {/* PASSWORD MATCH */}

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


              {/* PASSWORD MISMATCH */}

              {confirmPassword &&
                password !== confirmPassword && (
                  <div className="text-xs text-rose-600">
                    Passwords do not match.
                  </div>
                )}


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


              {/* SUCCESS */}

              {success && (
                <div
                  role="status"
                  aria-live="polite"
                  className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
                >
                  {success}
                </div>
              )}


              {/* CREATE ACCOUNT BUTTON */}

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

          )}


          {/* ==================================================
              STEP 2 — OTP VERIFICATION FORM
          ================================================== */}

          {step === 'otp' && (

            <form
              onSubmit={handleVerifyOTP}
              className="space-y-5"
            >

              {/* EMAIL DISPLAY */}

              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">

                <div className="flex items-center gap-3">

                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white">

                    <Mail
                      size={18}
                      className="text-teal-600"
                    />

                  </div>


                  <div className="min-w-0">

                    <p className="text-xs text-slate-500">
                      Verification code sent to
                    </p>

                    <p className="truncate text-sm font-medium text-slate-800">
                      {email}
                    </p>

                  </div>

                </div>

              </div>


              {/* OTP INPUT */}

              <div>

                <label
                  htmlFor="otp"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Verification code
                </label>


                <input
                  id="otp"
                  name="otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={otp}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                    setOtp(value);
                    setError('');
                  }}
                  placeholder="Enter 6-digit OTP"
                  maxLength={6}
                  required
                  autoFocus
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-center text-lg font-semibold tracking-[0.35em] outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />

                <p className="mt-2 text-xs text-slate-400">
                  Enter the 6-digit code sent to your email.
                </p>

              </div>


              {/* SUCCESS */}

              {success && (

                <div
                  role="status"
                  aria-live="polite"
                  className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
                >

                  <CheckCircle2
                    size={18}
                    className="mt-0.5 shrink-0"
                  />

                  <span>
                    {success}
                  </span>

                </div>

              )}


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


              {/* VERIFY BUTTON */}

              <Button
                type="submit"
                disabled={
                  loading ||
                  otp.length !== 6
                }
                className="w-full"
              >

                <ShieldCheck
                  size={18}
                  className="mr-2"
                />


                {loading
                  ? 'Verifying...'
                  : 'Verify & Activate Account'}

              </Button>


              {/* RESEND OTP */}

              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-slate-500">
                  Didn't receive the code?
                </span>

                <button
                  type="button"
                  onClick={handleResendOTP}
                  disabled={cooldown > 0 || resendLoading || loading}
                  className="inline-flex items-center gap-1 font-semibold text-teal-600 hover:text-teal-700 disabled:cursor-not-allowed disabled:text-slate-400"
                >
                  <RefreshCw
                    size={13}
                    className={resendLoading ? 'animate-spin' : ''}
                  />
                  {cooldown > 0
                    ? `Resend code (${cooldown}s)`
                    : resendLoading
                    ? 'Sending...'
                    : 'Resend code'}
                </button>
              </div>


              {/* EDIT REGISTRATION DETAILS / BACK */}

              <button
                type="button"
                onClick={() => {
                  setStep('form');
                  setError('');
                  setSuccess('');
                }}
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >

                <ArrowLeft
                  size={16}
                />

                Edit registration details

              </button>

            </form>

          )}


          {/* ==================================================
              LOGIN LINK
          ================================================== */}

          {step === 'form' && (

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

          )}


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