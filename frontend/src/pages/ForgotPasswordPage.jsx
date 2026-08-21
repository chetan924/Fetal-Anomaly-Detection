import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Mail,
  Send,
  ShieldCheck,
  KeyRound,
  RefreshCw,
} from 'lucide-react';

import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import {
  forgotPassword,
  verifyForgotPasswordOTP,
  resendForgotPasswordOTP,
  getApiErrorMessage,
} from '../services/api';

function ForgotPasswordPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState('email'); // 'email' | 'otp'
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');

  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [message, setMessage] = useState('');

  // ============================================================
  // COOLDOWN TIMER
  // ============================================================

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);


  // ============================================================
  // STEP 1 — SUBMIT EMAIL FOR OTP
  // ============================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError('');
    setMessage('');
    setSuccess(false);
    setLoading(true);

    try {
      const result = await forgotPassword(email.trim());

      setStep('otp');
      setOtp('');
      setCooldown(60);
      setMessage(
        result?.message ||
          'If an account exists for this email, a 6-digit verification code has been sent to your email.'
      );
      setSuccess(true);
    } catch (err) {
      console.error('Forgot password error:', err);
      setError(
        getApiErrorMessage(
          err,
          'Unable to process your request. Please try again.'
        )
      );
    } finally {
      setLoading(false);
    }
  };


  // ============================================================
  // STEP 2 — VERIFY OTP & NAVIGATE TO RESET PASSWORD
  // ============================================================

  const handleVerifyOTP = async (event) => {
    event.preventDefault();

    setError('');
    const normalizedOTP = otp.trim();

    if (!normalizedOTP || !/^\d{6}$/.test(normalizedOTP)) {
      setError('Please enter the 6-digit verification code.');
      return;
    }

    setLoading(true);

    try {
      const result = await verifyForgotPasswordOTP(email.trim(), normalizedOTP);

      if (result?.reset_token) {
        navigate(`/reset-password?token=${encodeURIComponent(result.reset_token)}`);
      } else {
        setError('OTP verified, but reset token missing.');
      }
    } catch (err) {
      console.error('Verify forgot password OTP error:', err);
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


  // ============================================================
  // RESEND OTP
  // ============================================================

  const handleResendOTP = async () => {
    if (cooldown > 0 || resendLoading) return;

    setError('');
    setResendLoading(true);

    try {
      const result = await resendForgotPasswordOTP(email.trim());
      setCooldown(60);
      setMessage(
        result?.message || 'A new verification code has been sent to your email.'
      );
    } catch (err) {
      console.error('Resend forgot password OTP error:', err);
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


  // ============================================================
  // SUCCESS VIEW
  // ============================================================

  if (success) {
    return (
      <main className="min-h-screen bg-slate-100 px-4 py-10">

        <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-md items-center justify-center">

          <Card className="w-full p-8">

            {/* Success Icon */}

            <div className="mb-6 flex justify-center">

              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">

                <CheckCircle2
                  size={32}
                  className="text-emerald-600"
                />

              </div>

            </div>


            {/* Header */}

            <div className="text-center">

              <h1 className="text-2xl font-bold text-slate-900">
                Check your email
              </h1>


              <p className="mt-3 text-sm leading-6 text-slate-600">
                {message}
              </p>


              {/* Security */}

              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left">

                <div className="flex gap-3">

                  <ShieldCheck
                    size={20}
                    className="mt-0.5 shrink-0 text-teal-600"
                  />

                  <p className="text-xs leading-5 text-slate-500">
                    For security, we do not reveal whether
                    an email address is registered with FetalAI.
                  </p>

                </div>

              </div>


              {/* =================================================
                  DEVELOPMENT ONLY RESET BUTTON
                  ================================================= */}

              {developmentToken && (
                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-left">

                  <div className="flex gap-3">

                    <KeyRound
                      size={20}
                      className="mt-0.5 shrink-0 text-amber-600"
                    />

                    <div>

                      <p className="text-sm font-semibold text-amber-800">
                        Development mode
                      </p>

                      <p className="mt-1 text-xs leading-5 text-amber-700">
                        Email delivery is not configured yet.
                        Use the button below to continue to
                        password reset.
                      </p>

                    </div>

                  </div>


                  <button
                    type="button"
                    onClick={handleDevelopmentReset}
                    className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-amber-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-amber-700"
                  >
                    <KeyRound size={17} />

                    Continue to reset password
                  </button>

                </div>
              )}


              {/* Actions */}

              <div className="mt-6 space-y-3">

                <button
                  type="button"
                  onClick={() => {
                    setSuccess(false);
                    setMessage('');
                    setEmail('');
                    setDevelopmentToken('');
                  }}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  Try another email
                </button>


                <Link
                  to="/login"
                  className="flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium text-teal-700 transition hover:bg-teal-50"
                >
                  <ArrowLeft size={16} />

                  Back to sign in
                </Link>

              </div>

            </div>

          </Card>

        </div>

      </main>
    );
  }

  // ============================================================
  // FORM VIEW
  // ============================================================

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">

      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-md items-center justify-center">

        <Card className="w-full p-8">

          {/* Header */}

          <div className="mb-6">

            <Link
              to="/login"
              className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-900"
            >
              <ArrowLeft size={16} />

              Back to sign in
            </Link>


            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-teal-600/10">

              {step === 'otp' ? (
                <ShieldCheck
                  size={24}
                  className="text-teal-600"
                />
              ) : (
                <Mail
                  size={24}
                  className="text-teal-600"
                />
              )}

            </div>


            <h1 className="text-2xl font-bold text-slate-900">
              {step === 'otp'
                ? 'Verify reset code'
                : 'Forgot your password?'}
            </h1>


            <p className="mt-2 text-sm leading-6 text-slate-600">
              {step === 'otp'
                ? 'Enter the 6-digit code sent to your email to reset your password.'
                : 'Enter the email address associated with your FetalAI account.'}
            </p>

          </div>


          {/* STEP 1 — EMAIL FORM */}

          {step === 'email' && (

            <form
              onSubmit={handleSubmit}
              className="space-y-5"
            >

              {/* Email */}

              <div>

                <label
                  htmlFor="forgot-email"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Email address
                </label>


                <div className="relative">

                  <Mail
                    size={18}
                    className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                  />


                  <input
                    id="forgot-email"
                    type="email"
                    value={email}
                    onChange={(event) =>
                      setEmail(event.target.value)
                    }
                    placeholder="doctor@example.com"
                    required
                    autoComplete="email"
                    disabled={loading}
                    className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                  />

                </div>

              </div>


              {/* Error */}

              {error && (
                <div
                  role="alert"
                  className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-5 text-rose-700"
                >
                  {error}
                </div>
              )}


              {/* Security */}

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

                <div className="flex gap-3">

                  <ShieldCheck
                    size={20}
                    className="mt-0.5 shrink-0 text-teal-600"
                  />

                  <div>

                    <p className="text-sm font-medium text-slate-700">
                      Your account is protected
                    </p>

                    <p className="mt-1 text-xs leading-5 text-slate-500">
                      A 6-digit verification code will be sent to your email.
                    </p>

                  </div>

                </div>

              </div>


              {/* Submit */}

              <Button
                type="submit"
                disabled={
                  loading ||
                  !email.trim()
                }
                className="w-full"
              >

                <Send
                  size={18}
                  className="mr-2"
                />

                {loading
                  ? 'Sending code...'
                  : 'Send verification code'}

              </Button>

            </form>

          )}


          {/* STEP 2 — OTP FORM */}

          {step === 'otp' && (

            <form
              onSubmit={handleVerifyOTP}
              className="space-y-5"
            >

              {/* Email Display */}

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


              {/* OTP Input */}

              <div>

                <label
                  htmlFor="forgot-otp"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Verification code
                </label>


                <input
                  id="forgot-otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={otp}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                    setOtp(val);
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


              {/* Message */}

              {message && (

                <div
                  role="status"
                  className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
                >

                  <CheckCircle2
                    size={18}
                    className="mt-0.5 shrink-0"
                  />

                  <span>{message}</span>

                </div>

              )}


              {/* Error */}

              {error && (

                <div
                  role="alert"
                  className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
                >
                  {error}
                </div>

              )}


              {/* Verify Button */}

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
                  : 'Verify & Continue'}

              </Button>


              {/* Resend OTP */}

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


              {/* Try another email */}

              <button
                type="button"
                onClick={() => {
                  setStep('email');
                  setError('');
                  setMessage('');
                  setOtp('');
                }}
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >

                <ArrowLeft size={16} />

                Try another email

              </button>

            </form>

          )}


          {/* Footer */}

          <div className="mt-6 border-t border-slate-200 pt-6 text-center">

            <p className="text-sm text-slate-500">
              Remember your password?
            </p>


            <Link
              to="/login"
              className="mt-1 inline-block text-sm font-semibold text-teal-600 transition hover:text-teal-700"
            >
              Sign in to FetalAI
            </Link>

          </div>

        </Card>

      </div>

    </main>
  );
}

export default ForgotPasswordPage;