import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  KeyRound,
  LogIn,
  Mail,
  RefreshCw,
  ShieldCheck,
  UserPlus,
} from 'lucide-react';

import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

import {
  getApiErrorMessage,
  login,
  verifyLoginOTP,
} from '../services/api';


function LoginPage() {
  const navigate = useNavigate();


  // ============================================================
  // LOGIN STATE
  // ============================================================

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [otp, setOtp] = useState('');

  const [step, setStep] = useState('credentials');

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState('');

  const [successMessage, setSuccessMessage] =
    useState('');


  // ============================================================
  // ERROR MESSAGE
  // ============================================================

  const getErrorMessage = (err, fallback) => {
    return getApiErrorMessage(
      err,
      fallback
    );
  };


  // ============================================================
  // LOGIN — STEP 1
  // ============================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError('');
    setSuccessMessage('');

    const normalizedEmail =
      email.trim();


    // ----------------------------------------------------------
    // VALIDATION
    // ----------------------------------------------------------

    if (!normalizedEmail) {
      setError(
        'Please enter your email address.'
      );
      return;
    }


    if (!password) {
      setError(
        'Please enter your password.'
      );
      return;
    }


    if (password.length < 8) {
      setError(
        'Password must be at least 8 characters.'
      );
      return;
    }


    setLoading(true);


    try {

      const result =
        await login(
          normalizedEmail,
          password
        );


      // --------------------------------------------------------
      // CASE 1
      // Backend already returned JWT.
      //
      // This keeps compatibility with the existing backend
      // behavior if OTP is disabled for some environment.
      // --------------------------------------------------------

      if (
        result?.access_token
      ) {

        localStorage.setItem(
          'access_token',
          result.access_token
        );


        const savedToken =
          localStorage.getItem(
            'access_token'
          );


        if (!savedToken) {
          throw new Error(
            'Authentication token could not be saved.'
          );
        }


        navigate('/', {
          replace: true,
        });

        return;
      }


      // --------------------------------------------------------
      // CASE 2
      // Backend requires OTP.
      // --------------------------------------------------------

      setStep('otp');

      setOtp('');

      setSuccessMessage(
        result?.message ||
        'A verification code has been sent. Enter the OTP to continue.'
      );

    } catch (err) {

      console.error(
        'Login error:',
        err
      );


      setError(
        getErrorMessage(
          err,
          'Login failed. Please check your credentials.'
        )
      );

    } finally {

      setLoading(false);
    }
  };


  // ============================================================
  // VERIFY LOGIN OTP
  // ============================================================

  const handleVerifyOTP = async (
    event
  ) => {

    event.preventDefault();

    setError('');
    setSuccessMessage('');


    const normalizedEmail =
      email.trim();

    const normalizedOTP =
      otp.trim();


    // ----------------------------------------------------------
    // VALIDATION
    // ----------------------------------------------------------

    if (!normalizedOTP) {
      setError(
        'Please enter the verification code.'
      );
      return;
    }


    if (!/^\d{6}$/.test(normalizedOTP)) {
      setError(
        'Please enter the 6-digit OTP.'
      );
      return;
    }


    setLoading(true);


    try {

      const result =
        await verifyLoginOTP(
          normalizedEmail,
          normalizedOTP
        );


      // --------------------------------------------------------
      // JWT VALIDATION
      // --------------------------------------------------------

      if (
        !result?.access_token
      ) {
        throw new Error(
          'OTP verified, but no authentication token was received.'
        );
      }


      // --------------------------------------------------------
      // SAVE JWT
      // --------------------------------------------------------

      localStorage.setItem(
        'access_token',
        result.access_token
      );


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
      // SUCCESS
      // --------------------------------------------------------

      setSuccessMessage(
        'Verification successful. Signing you in...'
      );


      navigate('/', {
        replace: true,
      });

    } catch (err) {

      console.error(
        'OTP verification error:',
        err
      );


      setError(
        getErrorMessage(
          err,
          'Invalid or expired OTP. Please try again.'
        )
      );

    } finally {

      setLoading(false);
    }
  };


  // ============================================================
  // CHANGE EMAIL
  // ============================================================

  const handleChangeEmail = () => {

    if (loading) {
      return;
    }

    setStep('credentials');

    setOtp('');

    setError('');

    setSuccessMessage('');
  };


  // ============================================================
  // OTP INPUT
  // ============================================================

  const handleOTPChange = (
    event
  ) => {

    const value =
      event.target.value
        .replace(/\D/g, '')
        .slice(0, 6);

    setOtp(value);

    setError('');
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

              {step === 'otp' ? (
                <ShieldCheck
                  size={24}
                  className="text-teal-600"
                />
              ) : (
                <LogIn
                  size={24}
                  className="text-teal-600"
                />
              )}

            </div>


            <h1 className="text-2xl font-semibold text-slate-900">

              {step === 'otp'
                ? 'Verify your identity'
                : 'Sign in'}

            </h1>


            <p className="mt-2 text-sm text-slate-500">

              {step === 'otp'
                ? 'Enter the 6-digit verification code to continue.'
                : 'Sign in to access the Fetal Anomaly Detection system.'}

            </p>

          </div>


          {/* ================================================== */}
          {/* STEP 1 — EMAIL + PASSWORD */}
          {/* ================================================== */}

          {step === 'credentials' && (

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
                    setEmail(
                      event.target.value
                    )
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
                    setPassword(
                      event.target.value
                    )
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


              {/* SIGN IN */}

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
                  ? 'Checking credentials...'
                  : 'Sign in'}

              </Button>

            </form>

          )}


          {/* ================================================== */}
          {/* STEP 2 — OTP */}
          {/* ================================================== */}

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


              {/* OTP */}

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
                  onChange={handleOTPChange}
                  placeholder="Enter 6-digit OTP"
                  maxLength={6}
                  required
                  autoFocus
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-center text-lg font-semibold tracking-[0.35em] outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />

                <p className="mt-2 text-xs text-slate-400">
                  Enter the 6-digit code generated for your account.
                </p>

              </div>


              {/* SUCCESS */}

              {successMessage && (

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
                    {successMessage}
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
                  : 'Verify & Sign in'}

              </Button>


              {/* CHANGE EMAIL */}

              <button
                type="button"
                onClick={handleChangeEmail}
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >

                <ArrowLeft
                  size={16}
                />

                Use a different email

              </button>

            </form>

          )}


          {/* ================================================== */}
          {/* SIGN UP */}
          {/* ================================================== */}

          {step === 'credentials' && (

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

          )}


          {/* ================================================== */}
          {/* OTP SECURITY INFO */}
          {/* ================================================== */}

          {step === 'otp' && (

            <div className="mt-5 flex items-start gap-3 rounded-xl bg-slate-50 px-4 py-3">

              <KeyRound
                size={17}
                className="mt-0.5 shrink-0 text-slate-400"
              />

              <p className="text-xs leading-5 text-slate-500">
                For security, a verification code is required before your account can be signed in.
              </p>

            </div>

          )}


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