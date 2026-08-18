import { useEffect, useState } from 'react';

import {
  UserCircle2,
  ShieldCheck,
  Bell,
  Brain,
  FileText,
  Palette,
  Server,
  LockKeyhole,
  Mail,
  CheckCircle2,
  Info,
  Save,
  Eye,
  EyeOff,
  AlertCircle,
} from 'lucide-react';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

import {
  changePassword,
  getCurrentUser,
  healthCheck,
} from '../services/api';


// ============================================================
// SETTINGS PAGE
// ============================================================

function SettingsPage() {

  // ==========================================================
  // PROFILE
  // ==========================================================

  const [fullName, setFullName] =
    useState('');

  const [email, setEmail] =
    useState('');

  const [role, setRole] =
    useState('');


  const [profileLoading, setProfileLoading] =
    useState(true);

  const [apiStatus, setApiStatus] =
    useState('checking');


  // ==========================================================
  // SECURITY
  // ==========================================================

  const [showPassword, setShowPassword] =
    useState(false);

  const [currentPassword, setCurrentPassword] =
    useState('');

  const [newPassword, setNewPassword] =
    useState('');

  const [confirmPassword, setConfirmPassword] =
    useState('');

  const [passwordLoading, setPasswordLoading] =
    useState(false);

  const [passwordError, setPasswordError] =
    useState('');

  const [passwordSuccess, setPasswordSuccess] =
    useState('');


  // ==========================================================
  // NOTIFICATIONS
  // ==========================================================

  const [scanNotifications, setScanNotifications] =
    useState(true);

  const [screeningNotifications, setScreeningNotifications] =
    useState(true);

  const [errorNotifications, setErrorNotifications] =
    useState(true);

  const [systemNotifications, setSystemNotifications] =
    useState(true);


  // ==========================================================
  // PREFERENCES
  // ==========================================================

  const [theme, setTheme] =
    useState('system');

  const [language, setLanguage] =
    useState('English');

  const [defaultView, setDefaultView] =
    useState('dashboard');


  // ==========================================================
  // REPORT SETTINGS
  // ==========================================================

  const [includeConfidence, setIncludeConfidence] =
    useState(true);

  const [includeMethodology, setIncludeMethodology] =
    useState(true);

  const [includeDisclaimer, setIncludeDisclaimer] =
    useState(true);


  // ==========================================================
  // SAVE STATE
  // ==========================================================

  const [saved, setSaved] =
    useState(false);


  // ==========================================================
  // LOAD CURRENT USER
  // ==========================================================

  useEffect(() => {

    let mounted = true;


    const loadUser = async () => {

      try {

        setProfileLoading(true);

        const user =
          await getCurrentUser();


        if (!mounted) {
          return;
        }


        setFullName(
          user?.full_name ||
          user?.name ||
          ''
        );


        setEmail(
          user?.email ||
          ''
        );


        setRole(
          user?.role ||
          'Doctor'
        );


      } catch (error) {

        console.error(
          'Failed to load current user:',
          error
        );


        if (!mounted) {
          return;
        }


        /*
         * Keep a safe fallback if the profile
         * endpoint is temporarily unavailable.
         */

        setFullName(
          'Doctor'
        );

        setRole(
          'Clinical User'
        );

      } finally {

        if (mounted) {
          setProfileLoading(false);
        }

      }

    };


    loadUser();


    return () => {
      mounted = false;
    };

  }, []);


  // ==========================================================
  // API STATUS
  // ==========================================================

  useEffect(() => {

    let mounted = true;

    const checkApi = async () => {

      try {

        await healthCheck();

        if (mounted) {
          setApiStatus('connected');
        }

      } catch (error) {

        console.error(
          'FetalAI API health check failed:',
          error
        );

        if (mounted) {
          setApiStatus('offline');
        }

      }

    };

    checkApi();

    const intervalId =
      window.setInterval(
        checkApi,
        30000
      );

    return () => {

      mounted = false;

      window.clearInterval(
        intervalId
      );

    };

  }, []);


  // LOAD SAVED SETTINGS
  // ==========================================================

  useEffect(() => {

    try {

      const stored =
        localStorage.getItem(
          'fetalai_settings'
        );


      if (!stored) {
        return;
      }


      const settings =
        JSON.parse(stored);


      if (settings.fullName) {
        setFullName(
          settings.fullName
        );
      }


      if (settings.email) {
        setEmail(
          settings.email
        );
      }


      if (
        settings.notifications
      ) {

        setScanNotifications(
          settings.notifications
            .scanNotifications ??
          true
        );

        setScreeningNotifications(
          settings.notifications
            .screeningNotifications ??
          true
        );

        setErrorNotifications(
          settings.notifications
            .errorNotifications ??
          true
        );

        setSystemNotifications(
          settings.notifications
            .systemNotifications ??
          true
        );

      }


      if (
        settings.preferences
      ) {

        setTheme(
          settings.preferences
            .theme ??
          'system'
        );

        setLanguage(
          settings.preferences
            .language ??
          'English'
        );

        setDefaultView(
          settings.preferences
            .defaultView ??
          'dashboard'
        );

      }


      if (
        settings.reports
      ) {

        setIncludeConfidence(
          settings.reports
            .includeConfidence ??
          true
        );

        setIncludeMethodology(
          settings.reports
            .includeMethodology ??
          true
        );

        setIncludeDisclaimer(
          settings.reports
            .includeDisclaimer ??
          true
        );

      }

    } catch (error) {

      console.error(
        'Failed to load saved settings:',
        error
      );

    }

  }, []);


  // ==========================================================
  // SAVE SETTINGS
  // ==========================================================

  const handleSave = () => {

    const settings = {

      fullName,

      email,

      notifications: {
        scanNotifications,
        screeningNotifications,
        errorNotifications,
        systemNotifications,
      },

      preferences: {
        theme,
        language,
        defaultView,
      },

      reports: {
        includeConfidence,
        includeMethodology,
        includeDisclaimer,
      },

    };


    localStorage.setItem(
      'fetalai_settings',
      JSON.stringify(
        settings
      )
    );


    window.dispatchEvent(
      new CustomEvent(
        'fetalai-settings-updated',
        {
          detail: settings,
        }
      )
    );


    setSaved(true);


    window.setTimeout(() => {
      setSaved(false);
    }, 2500);

  };


  // ==========================================================
  // CHANGE PASSWORD
  // ==========================================================

  const handleChangePassword =
    async () => {

      setPasswordError('');
      setPasswordSuccess('');


      // ------------------------------------------------------
      // REQUIRED FIELDS
      // ------------------------------------------------------

      if (
        !currentPassword ||
        !newPassword ||
        !confirmPassword
      ) {

        setPasswordError(
          'Please fill in all password fields.'
        );

        return;
      }


      // ------------------------------------------------------
      // PASSWORD LENGTH
      // ------------------------------------------------------

      if (
        newPassword.length < 8
      ) {

        setPasswordError(
          'New password must contain at least 8 characters.'
        );

        return;
      }


      // ------------------------------------------------------
      // CONFIRM PASSWORD
      // ------------------------------------------------------

      if (
        newPassword !==
        confirmPassword
      ) {

        setPasswordError(
          'New password and confirmation do not match.'
        );

        return;
      }


      // ------------------------------------------------------
      // PREVENT SAME PASSWORD
      // ------------------------------------------------------

      if (
        currentPassword ===
        newPassword
      ) {

        setPasswordError(
          'New password must be different from your current password.'
        );

        return;
      }


      try {

        setPasswordLoading(true);


        await changePassword(
          currentPassword,
          newPassword
        );


        // ----------------------------------------------------
        // CLEAR FIELDS
        // ----------------------------------------------------

        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');


        // ----------------------------------------------------
        // SUCCESS
        // ----------------------------------------------------

        setPasswordSuccess(
          'Password changed successfully.'
        );


      } catch (error) {

        console.error(
          'Change password error:',
          error
        );


        const detail =
          error?.response?.data?.detail;


        let message =
          'Unable to change password. Please try again.';


        if (
          Array.isArray(detail)
        ) {

          message =
            detail
              .map(
                (item) =>
                  item?.msg ||
                  String(item)
              )
              .join(', ');

        } else if (
          typeof detail ===
          'string'
        ) {

          message = detail;

        } else if (
          error?.response?.data?.message
        ) {

          message =
            error.response.data.message;

        } else if (
          error?.message
        ) {

          message =
            error.message;

        }


        setPasswordError(
          message
        );

      } finally {

        setPasswordLoading(false);

      }

    };


  // ==========================================================
  // TOGGLE COMPONENT
  // ==========================================================

  const Toggle = ({
    enabled,
    onChange,
    label,
    description,
  }) => (

    <button
      type="button"
      onClick={() =>
        onChange(!enabled)
      }
      className="flex w-full items-center justify-between gap-4 rounded-xl px-3 py-3 text-left transition hover:bg-slate-50"
    >

      <div className="min-w-0">

        <p className="text-sm font-medium text-slate-800">
          {label}
        </p>


        {description && (

          <p className="mt-1 text-xs leading-5 text-slate-500">
            {description}
          </p>

        )}

      </div>


      <span
        className={`relative h-6 w-11 shrink-0 rounded-full transition ${
          enabled
            ? 'bg-teal-600'
            : 'bg-slate-300'
        }`}
      >

        <span
          className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow-sm transition ${
            enabled
              ? 'left-6'
              : 'left-1'
          }`}
        />

      </span>

    </button>

  );


  // ==========================================================
  // SECTION HEADER
  // ==========================================================

  const SectionHeader = ({
    icon,
    title,
    description,
  }) => (

    <div className="mb-5 flex items-start gap-3">

      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-600">

        {icon}

      </div>


      <div>

        <h2 className="text-base font-semibold text-slate-900">
          {title}
        </h2>


        <p className="mt-1 text-sm text-slate-500">
          {description}
        </p>

      </div>

    </div>

  );


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="space-y-6">

      {/* ====================================================
          HEADER
      ==================================================== */}

      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">

        <div>

          <h1 className="text-2xl font-semibold text-slate-900">
            Settings
          </h1>


          <p className="mt-2 text-sm text-slate-500">
            Manage your FetalAI clinical workspace,
            security and preferences.
          </p>

        </div>


        <Button
          type="button"
          onClick={handleSave}
        >

          {saved ? (

            <CheckCircle2
              size={17}
              className="mr-2"
            />

          ) : (

            <Save
              size={17}
              className="mr-2"
            />

          )}


          {saved
            ? 'Settings saved'
            : 'Save changes'}

        </Button>

      </div>


      {/* ====================================================
          PROFILE
      ==================================================== */}

      <Card>

        <SectionHeader
          icon={
            <UserCircle2 size={20} />
          }
          title="Profile"
          description="Manage your professional account information."
        />


        <div className="grid gap-5 md:grid-cols-2">

          {/* FULL NAME */}

          <div>

            <label
              htmlFor="full-name"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Full name
            </label>


            <input
              id="full-name"
              value={
                profileLoading
                  ? 'Loading...'
                  : fullName
              }
              onChange={(event) =>
                setFullName(
                  event.target.value
                )
              }
              disabled={
                profileLoading
              }
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-50"
            />

          </div>


          {/* EMAIL */}

          <div>

            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Email address
            </label>


            <div className="relative">

              <Mail
                size={17}
                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
              />


              <input
                id="email"
                type="email"
                value={
                  profileLoading
                    ? 'Loading...'
                    : email
                }
                disabled
                className="w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 pl-11 text-sm text-slate-500"
              />

            </div>


            <p className="mt-1 text-xs text-slate-400">
              Email is managed by your account.
            </p>

          </div>


          {/* ROLE */}

          <div>

            <label
              htmlFor="role"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Role
            </label>


            <input
              id="role"
              value={
                profileLoading
                  ? 'Loading...'
                  : role
              }
              disabled
              className="w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500"
            />

          </div>


          {/* ACCOUNT STATUS */}

          <div>

            <label className="mb-2 block text-sm font-medium text-slate-700">
              Account status
            </label>


            <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">

              <CheckCircle2
                size={17}
                className="text-emerald-600"
              />


              <span className="text-sm font-medium text-emerald-700">
                Active account
              </span>

            </div>

          </div>

        </div>

      </Card>


      {/* ====================================================
          SECURITY
      ==================================================== */}

      <Card>

        <SectionHeader
          icon={
            <ShieldCheck size={20} />
          }
          title="Security"
          description="Protect your FetalAI account and authentication."
        />


        <div className="space-y-5">

          {/* SECURITY INTRO */}

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

            <div className="flex items-start gap-3">

              <LockKeyhole
                size={19}
                className="mt-0.5 text-slate-500"
              />


              <div>

                <p className="text-sm font-semibold text-slate-800">
                  Change password
                </p>


                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Use a strong password that is unique
                  to your FetalAI account.
                </p>

              </div>

            </div>

          </div>


          {/* PASSWORD ERROR */}

          {passwordError && (

            <div
              role="alert"
              className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3"
            >

              <AlertCircle
                size={18}
                className="mt-0.5 shrink-0 text-rose-600"
              />


              <p className="text-sm text-rose-700">
                {passwordError}
              </p>

            </div>

          )}


          {/* PASSWORD SUCCESS */}

          {passwordSuccess && (

            <div
              role="status"
              className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3"
            >

              <CheckCircle2
                size={18}
                className="mt-0.5 shrink-0 text-emerald-600"
              />


              <p className="text-sm text-emerald-700">
                {passwordSuccess}
              </p>

            </div>

          )}


          {/* PASSWORD FIELDS */}

          <div className="grid gap-5 md:grid-cols-3">

            {/* CURRENT */}

            <div>

              <label
                htmlFor="current-password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Current password
              </label>


              <input
                id="current-password"
                type={
                  showPassword
                    ? 'text'
                    : 'password'
                }
                value={
                  currentPassword
                }
                onChange={(event) =>
                  setCurrentPassword(
                    event.target.value
                  )
                }
                disabled={
                  passwordLoading
                }
                autoComplete="current-password"
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-50"
              />

            </div>


            {/* NEW */}

            <div>

              <label
                htmlFor="new-password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                New password
              </label>


              <input
                id="new-password"
                type={
                  showPassword
                    ? 'text'
                    : 'password'
                }
                value={
                  newPassword
                }
                onChange={(event) =>
                  setNewPassword(
                    event.target.value
                  )
                }
                disabled={
                  passwordLoading
                }
                autoComplete="new-password"
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-50"
              />

            </div>


            {/* CONFIRM */}

            <div>

              <label
                htmlFor="confirm-password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Confirm password
              </label>


              <input
                id="confirm-password"
                type={
                  showPassword
                    ? 'text'
                    : 'password'
                }
                value={
                  confirmPassword
                }
                onChange={(event) =>
                  setConfirmPassword(
                    event.target.value
                  )
                }
                disabled={
                  passwordLoading
                }
                autoComplete="new-password"
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-50"
              />

            </div>

          </div>


          {/* PASSWORD CONTROLS */}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

            <button
              type="button"
              onClick={() =>
                setShowPassword(
                  (value) =>
                    !value
                )
              }
              className="inline-flex items-center self-start text-sm font-medium text-teal-600 hover:text-teal-700"
            >

              {showPassword ? (

                <EyeOff
                  size={16}
                  className="mr-2"
                />

              ) : (

                <Eye
                  size={16}
                  className="mr-2"
                />

              )}


              {showPassword
                ? 'Hide passwords'
                : 'Show passwords'}

            </button>


            <Button
              type="button"
              onClick={
                handleChangePassword
              }
              disabled={
                passwordLoading ||
                !currentPassword ||
                !newPassword ||
                !confirmPassword
              }
            >

              {passwordLoading
                ? 'Changing password...'
                : 'Change password'}

            </Button>

          </div>


          {/* PASSWORD NOTE */}

          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">

            <p className="text-xs leading-5 text-amber-800">

              Password changes are processed through
              the authenticated FetalAI backend.
              Your current password is never stored
              in browser settings.

            </p>

          </div>

        </div>

      </Card>


      {/* ====================================================
          NOTIFICATIONS
      ==================================================== */}

      <Card>

        <SectionHeader
          icon={
            <Bell size={20} />
          }
          title="Notifications"
          description="Choose which FetalAI events should appear in your workspace."
        />


        <div className="divide-y divide-slate-100">

          <Toggle
            enabled={
              scanNotifications
            }
            onChange={
              setScanNotifications
            }
            label="Scan analysis completed"
            description="Notify when an ultrasound analysis finishes successfully."
          />


          <Toggle
            enabled={
              screeningNotifications
            }
            onChange={
              setScreeningNotifications
            }
            label="Statistical screening alerts"
            description="Notify when experimental statistical screening requires clinical review."
          />


          <Toggle
            enabled={
              errorNotifications
            }
            onChange={
              setErrorNotifications
            }
            label="Analysis failures"
            description="Notify when an uploaded scan cannot be processed."
          />


          <Toggle
            enabled={
              systemNotifications
            }
            onChange={
              setSystemNotifications
            }
            label="System notifications"
            description="Notify about important platform and system events."
          />

        </div>

      </Card>


      {/* ====================================================
          AI & ANALYSIS
      ==================================================== */}

      <Card>

        <SectionHeader
          icon={
            <Brain size={20} />
          }
          title="AI & Analysis"
          description="Review the configuration used by the FetalAI analysis pipeline."
        />


        <div className="space-y-4">

          {/* FETAL MODEL */}

          <div className="rounded-2xl border border-slate-200 p-4">

            <div className="flex items-start justify-between gap-4">

              <div>

                <p className="text-sm font-semibold text-slate-900">
                  Fetal plane classifier
                </p>


                <p className="mt-1 text-xs text-slate-500">
                  EfficientNet-B0 based image classification model.
                </p>

              </div>


              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                Ready
              </span>

            </div>


            <div className="mt-4 grid gap-3 sm:grid-cols-3">

              <div className="rounded-xl bg-slate-50 p-3">

                <p className="text-xs text-slate-500">
                  Model
                </p>


                <p className="mt-1 text-sm font-semibold text-slate-800">
                  EfficientNet-B0
                </p>

              </div>


              <div className="rounded-xl bg-slate-50 p-3">

                <p className="text-xs text-slate-500">
                  Input
                </p>


                <p className="mt-1 text-sm font-semibold text-slate-800">
                  224 × 224
                </p>

              </div>


              <div className="rounded-xl bg-slate-50 p-3">

                <p className="text-xs text-slate-500">
                  Status
                </p>


                <p className="mt-1 text-sm font-semibold text-emerald-700">
                  Active
                </p>

              </div>

            </div>

          </div>


          {/* BRAIN THRESHOLD */}

          <div className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-4">

            <div>

              <p className="text-sm font-semibold text-slate-800">
                Brain-plane confidence threshold
              </p>


              <p className="mt-1 text-xs leading-5 text-slate-500">
                Automatic brain-specific analysis requires sufficient model confidence.
              </p>

            </div>


            <span className="shrink-0 rounded-xl bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700">
              70%
            </span>

          </div>


          {/* EXPERIMENTAL SCREENING */}

          <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">

            <Info
              size={18}
              className="mt-0.5 shrink-0 text-amber-700"
            />


            <p className="text-xs leading-5 text-amber-800">

              Statistical outlier screening is experimental
              and must not be interpreted as a clinically
              validated fetal anomaly diagnosis.

            </p>

          </div>

        </div>

      </Card>


      {/* ====================================================
          REPORTS
      ==================================================== */}

      <Card>

        <SectionHeader
          icon={
            <FileText size={20} />
          }
          title="Reports & Clinical Workflow"
          description="Configure which information is included in generated reports."
        />


        <div className="divide-y divide-slate-100">

          <Toggle
            enabled={
              includeConfidence
            }
            onChange={
              setIncludeConfidence
            }
            label="Include AI confidence"
            description="Show model confidence values in generated reports."
          />


          <Toggle
            enabled={
              includeMethodology
            }
            onChange={
              setIncludeMethodology
            }
            label="Include analysis methodology"
            description="Include a concise description of the AI-assisted analysis pipeline."
          />


          <Toggle
            enabled={
              includeDisclaimer
            }
            onChange={
              setIncludeDisclaimer
            }
            label="Include clinical disclaimer"
            description="Include the required experimental-analysis and clinical-review disclaimer."
          />

        </div>

      </Card>


      {/* ====================================================
          APPEARANCE
      ==================================================== */}

      <Card>

        <SectionHeader
          icon={
            <Palette size={20} />
          }
          title="Appearance & Preferences"
          description="Customize how the FetalAI workspace behaves."
        />


        <div className="grid gap-5 md:grid-cols-3">

          {/* THEME */}

          <div>

            <label
              htmlFor="theme"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Theme
            </label>


            <select
              id="theme"
              value={theme}
              onChange={(event) =>
                setTheme(
                  event.target.value
                )
              }
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
            >

              <option value="system">
                System default
              </option>

              <option value="light">
                Light
              </option>

              <option value="dark">
                Dark
              </option>

            </select>

          </div>


          {/* LANGUAGE */}

          <div>

            <label
              htmlFor="language"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Language
            </label>


            <select
              id="language"
              value={language}
              onChange={(event) =>
                setLanguage(
                  event.target.value
                )
              }
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
            >

              <option value="English">
                English
              </option>

              <option value="Hindi">
                Hindi
              </option>

              <option value="Marathi">
                Marathi
              </option>

            </select>

          </div>


          {/* DEFAULT VIEW */}

          <div>

            <label
              htmlFor="default-view"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Default view
            </label>


            <select
              id="default-view"
              value={defaultView}
              onChange={(event) =>
                setDefaultView(
                  event.target.value
                )
              }
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
            >

              <option value="dashboard">
                Dashboard
              </option>

              <option value="new-scan">
                New Scan
              </option>

              <option value="patients">
                Patients
              </option>

              <option value="analytics">
                Analytics
              </option>

            </select>

          </div>

        </div>

      </Card>


      {/* ====================================================
          SYSTEM INFORMATION
      ==================================================== */}

      <Card>

        <SectionHeader
          icon={
            <Server size={20} />
          }
          title="System Information"
          description="Current FetalAI platform and service information."
        />


        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

          {/* PLATFORM */}

          <div className="rounded-xl border border-slate-200 p-4">

            <p className="text-xs text-slate-500">
              Platform
            </p>


            <p className="mt-1 text-sm font-semibold text-slate-900">
              FetalAI
            </p>

          </div>


          {/* API */}

          <div className="rounded-xl border border-slate-200 p-4">

            <p className="text-xs text-slate-500">
              API
            </p>


            <div className="mt-1 flex items-center gap-2">

              <span
                className={`h-2 w-2 rounded-full ${
                  apiStatus === 'connected'
                    ? 'bg-emerald-500'
                    : apiStatus === 'offline'
                      ? 'bg-rose-500'
                      : 'bg-amber-400'
                }`}
              />

              <p
                className={`text-sm font-semibold ${
                  apiStatus === 'connected'
                    ? 'text-emerald-700'
                    : apiStatus === 'offline'
                      ? 'text-rose-700'
                      : 'text-amber-700'
                }`}
              >
                {apiStatus === 'connected'
                  ? 'Connected'
                  : apiStatus === 'offline'
                    ? 'Offline'
                    : 'Checking...'}
              </p>

            </div>

          </div>


          {/* AI */}

          <div className="rounded-xl border border-slate-200 p-4">

            <p className="text-xs text-slate-500">
              AI Pipeline
            </p>


            <div className="mt-1 flex items-center gap-2">

              <span
                className={`h-2 w-2 rounded-full ${
                  apiStatus === 'connected'
                    ? 'bg-emerald-500'
                    : apiStatus === 'offline'
                      ? 'bg-rose-500'
                      : 'bg-amber-400'
                }`}
              />

              <p
                className={`text-sm font-semibold ${
                  apiStatus === 'connected'
                    ? 'text-emerald-700'
                    : apiStatus === 'offline'
                      ? 'text-rose-700'
                      : 'text-amber-700'
                }`}
              >
                {apiStatus === 'connected'
                  ? 'Ready'
                  : apiStatus === 'offline'
                    ? 'Unavailable'
                    : 'Checking...'}
              </p>

            </div>

          </div>


          {/* VERSION */}

          <div className="rounded-xl border border-slate-200 p-4">

            <p className="text-xs text-slate-500">
              Application
            </p>


            <p className="mt-1 text-sm font-semibold text-slate-900">
              v1.0
            </p>

          </div>

        </div>

      </Card>


      {/* ====================================================
          CLINICAL DISCLAIMER
      ==================================================== */}

      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">

        <div className="flex items-start gap-3">

          <Info
            size={19}
            className="mt-0.5 shrink-0 text-amber-700"
          />


          <div>

            <p className="text-sm font-semibold text-amber-900">
              Clinical AI notice
            </p>


            <p className="mt-1 text-xs leading-5 text-amber-800">

              FetalAI provides AI-assisted screening
              and statistical analysis outputs for
              clinical review. These outputs should
              not be treated as a standalone clinically
              validated diagnosis.

            </p>

          </div>

        </div>

      </div>

    </div>

  );
}


export default SettingsPage;