import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  Activity,
  Brain,
  CheckCircle2,
  FileText,
  ScanLine,
  Upload,
  UserPlus,
  Users,
  AlertTriangle,
  Database,
  Server,
  RefreshCw,
} from 'lucide-react';

import PageHeader from '../components/common/PageHeader';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

import {
  getPatients,
  getScans,
  healthCheck,
} from '../services/api';

const statIcons = {
  'Total Scans': ScanLine,
  'Normal Scans': CheckCircle2,
  'Flagged Scans': AlertTriangle,
  'Patients': Users,
};

const toneClasses = {
  primary: 'bg-cyan-50 text-cyan-700',
  success: 'bg-emerald-50 text-emerald-700',
  danger: 'bg-red-50 text-red-700',
  warning: 'bg-amber-50 text-amber-700',
};

function DashboardPage() {
  const navigate = useNavigate();

  const [patients, setPatients] = useState([]);
  const [scans, setScans] = useState([]);
  const [backendStatus, setBackendStatus] = useState('Checking...');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError('');

      const [patientsResult, scansResult, healthResult] =
        await Promise.all([
          getPatients(),
          getScans(),
          healthCheck(),
        ]);

      setPatients(
        Array.isArray(patientsResult)
          ? patientsResult
          : patientsResult?.patients || []
      );

      setScans(
        Array.isArray(scansResult)
          ? scansResult
          : scansResult?.scans || []
      );

      // /health currently returns a successful response such as:
      // { message: "FetalAI backend is running" }.
      // A successful request is therefore the reliable online signal.
      setBackendStatus(
        healthResult
          ? 'Online'
          : 'Unavailable'
      );
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          'Unable to load dashboard data.'
      );

      setBackendStatus('Offline');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const statistics = useMemo(() => {
    const totalScans = scans.length;

    const brainScans = scans.filter(
      (scan) =>
        scan.predicted_plane === 'Fetal brain'
    ).length;

    const flaggedScans = scans.filter(
      (scan) => {
        const analysis =
          scan.analysis_result || {};

        const outlier =
          analysis.outlier_analysis || {};

        return (
          scan.is_outlier === true ||
          scan.status === 'Unusual / Outlier' ||
          outlier.is_outlier === true ||
          outlier.status === 'Outlier' ||
          outlier.status === 'Unusual / Outlier'
        );
      }
    ).length;

    const normalScans =
      totalScans - flaggedScans;

    const averageConfidence =
      totalScans > 0
        ? scans.reduce(
            (sum, scan) =>
              sum + Number(scan.confidence || 0),
            0
          ) / totalScans
        : 0;

    return {
      totalScans,
      brainScans,
      flaggedScans,
      normalScans,
      patients: patients.length,
      averageConfidence,
    };
  }, [patients, scans]);

  const recentScans = useMemo(() => {
    return [...scans]
      .sort(
        (a, b) =>
          new Date(b.created_at || 0) -
          new Date(a.created_at || 0)
      )
      .slice(0, 5);
  }, [scans]);

  const monthlyScans = useMemo(() => {
    const months = [];

    for (let i = 5; i >= 0; i -= 1) {
      const date = new Date();

      date.setMonth(
        date.getMonth() - i
      );

      months.push({
        key: `${date.getFullYear()}-${date.getMonth()}`,
        label: date.toLocaleString(
          'en-US',
          { month: 'short' }
        ),
        count: 0,
      });
    }

    scans.forEach((scan) => {
      if (!scan.created_at) return;

      const date = new Date(
        scan.created_at
      );

      const key = `${date.getFullYear()}-${date.getMonth()}`;

      const month = months.find(
        (item) => item.key === key
      );

      if (month) {
        month.count += 1;
      }
    });

    return months;
  }, [scans]);

  const maxMonthlyScans = Math.max(
    ...monthlyScans.map(
      (item) => item.count
    ),
    1
  );

  const stats = [
    {
      id: 1,
      label: 'Total Scans',
      value: statistics.totalScans,
      trend: `${statistics.brainScans} fetal-brain scans`,
      tone: 'primary',
    },
    {
      id: 2,
      label: 'Normal Scans',
      value: statistics.normalScans,
      trend:
        statistics.totalScans > 0
          ? 'Based on available analysis data'
          : 'No scan data yet',
      tone: 'success',
    },
    {
      id: 3,
      label: 'Flagged Scans',
      value: statistics.flaggedScans,
      trend: 'Statistical outlier results',
      tone: 'danger',
    },
    {
      id: 4,
      label: 'Patients',
      value: statistics.patients,
      trend: 'Registered patients',
      tone: 'primary',
    },
    {
      id: 5,
      label: 'Avg. Confidence',
      value: `${(
        statistics.averageConfidence * 100
      ).toFixed(1)}%`,
      trend: 'Across completed scans',
      tone: 'success',
    },
  ];

  return (
    <div className="space-y-6">

      <PageHeader
        title="Welcome back, Doctor"
        subtitle="AI-assisted fetal ultrasound screening workspace."
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={loadDashboard}
              disabled={loading}
            >
              <RefreshCw
                size={17}
                className={`mr-2 ${
                  loading
                    ? 'animate-spin'
                    : ''
                }`}
              />
              Refresh
            </Button>

            <Button
              onClick={() =>
                navigate('/new-scan')
              }
            >
              <ScanLine
                size={18}
                className="mr-2"
              />
              Start New Scan
            </Button>
          </div>
        }
      />

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* REAL STATISTICS */}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {stats.map((stat) => {
          const Icon =
            statIcons[stat.label] ||
            Activity;

          return (
            <div
              key={stat.id}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-500">
                    {stat.label}
                  </p>

                  <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
                    {loading
                      ? '—'
                      : stat.value}
                  </p>
                </div>

                <div
                  className={`rounded-xl p-3 ${
                    toneClasses[
                      stat.tone
                    ]
                  }`}
                >
                  <Icon size={21} />
                </div>
              </div>

              <p className="mt-4 text-xs text-slate-400">
                {stat.trend}
              </p>
            </div>
          );
        })}
      </section>

      {/* MAIN */}

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.75fr]">

        <Card
          title="New Scan Analysis"
          subtitle="Upload a prenatal ultrasound image for AI-assisted screening."
        >
          <div className="flex min-h-[360px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 px-6 text-center">

            <div className="rounded-2xl bg-cyan-50 p-4 text-cyan-700">
              <Upload size={30} />
            </div>

            <h3 className="mt-5 text-lg font-semibold text-slate-900">
              Upload Ultrasound Image
            </h3>

            <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
              Select a prenatal ultrasound
              image to begin a new screening
              session.
            </p>

            <Button
              className="mt-5"
              onClick={() =>
                navigate('/new-scan')
              }
            >
              Select Image
            </Button>

            <p className="mt-3 text-xs text-slate-400">
              AI inference is connected to
              the backend analysis pipeline.
            </p>
          </div>
        </Card>

        {/* RECENT SCANS */}

        <div className="space-y-6">

          <Card
            title="Recent Scans"
            subtitle="Latest screening activity"
          >
            {recentScans.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-8 text-center">

                <ScanLine
                  className="mx-auto text-slate-400"
                  size={28}
                />

                <p className="mt-3 text-sm font-medium text-slate-700">
                  No scans yet
                </p>

                <p className="mt-1 text-xs text-slate-500">
                  Completed scans will
                  appear here.
                </p>

              </div>
            ) : (
              <div className="space-y-3">

                {recentScans.map(
                  (scan) => (
                    <button
                      key={scan.id}
                      type="button"
                      onClick={() =>
                        navigate(
                          `/reports?scan=${scan.id}`
                        )
                      }
                      className="w-full rounded-xl border border-slate-200 p-4 text-left transition hover:border-cyan-300 hover:bg-cyan-50"
                    >
                      <div className="flex items-start justify-between gap-3">

                        <div>
                          <p className="text-sm font-semibold text-slate-900">
                            Scan #{scan.id}
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            {scan.patient_id}
                            {' — '}
                            {scan.patient_name}
                          </p>
                        </div>

                        <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-medium text-cyan-700">
                          {scan.predicted_plane}
                        </span>

                      </div>

                      <div className="mt-3 flex justify-between text-xs text-slate-400">

                        <span>
                          {scan.created_at
                            ? new Date(
                                scan.created_at
                              ).toLocaleString()
                            : '—'}
                        </span>

                        <span>
                          {(
                            Number(
                              scan.confidence ||
                                0
                            ) * 100
                          ).toFixed(2)}
                          %
                        </span>

                      </div>
                    </button>
                  )
                )}

              </div>
            )}
          </Card>

          {/* QUICK ACTIONS */}

          <Card title="Quick Actions">

            <div className="grid grid-cols-2 gap-3">

              <button
                type="button"
                onClick={() =>
                  navigate('/new-scan')
                }
                className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-cyan-300 hover:bg-cyan-50"
              >
                <ScanLine
                  size={20}
                  className="text-cyan-700"
                />

                <p className="mt-3 text-sm font-semibold text-slate-900">
                  New Scan
                </p>
              </button>

              <button
                type="button"
                onClick={() =>
                  navigate('/patients')
                }
                className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-cyan-300 hover:bg-cyan-50"
              >
                <UserPlus
                  size={20}
                  className="text-cyan-700"
                />

                <p className="mt-3 text-sm font-semibold text-slate-900">
                  Add Patient
                </p>
              </button>

              <button
                type="button"
                onClick={() =>
                  navigate('/reports')
                }
                className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-cyan-300 hover:bg-cyan-50"
              >
                <FileText
                  size={20}
                  className="text-cyan-700"
                />

                <p className="mt-3 text-sm font-semibold text-slate-900">
                  Reports
                </p>
              </button>

              <button
                type="button"
                onClick={() =>
                  navigate('/analytics')
                }
                className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-cyan-300 hover:bg-cyan-50"
              >
                <Activity
                  size={20}
                  className="text-cyan-700"
                />

                <p className="mt-3 text-sm font-semibold text-slate-900">
                  Analytics
                </p>
              </button>

            </div>

          </Card>
        </div>
      </section>

      {/* ANALYTICS */}

      <section className="grid gap-6 xl:grid-cols-3">

        {/* MONTHLY */}

        <Card
          title="Monthly Scan Overview"
          subtitle="Based on actual scan timestamps."
        >
          <div className="flex h-56 items-end gap-3 rounded-2xl bg-slate-50 p-5">

            {monthlyScans.map(
              (item) => (
                <div
                  key={item.key}
                  className="flex flex-1 flex-col items-center justify-end gap-3"
                >
                  <div
                    className="w-full max-w-10 rounded-t-lg bg-cyan-500 transition-all"
                    style={{
                      height: `${Math.max(
                        (item.count /
                          maxMonthlyScans) *
                          120,
                        item.count > 0
                          ? 12
                          : 4
                      )}px`,
                    }}
                    title={`${item.count} scan(s)`}
                  />

                  <span className="text-xs text-slate-500">
                    {item.label}
                  </span>
                </div>
              )
            )}

          </div>
        </Card>

        {/* BRAIN */}

        <Card
          title="AI Plane Distribution"
          subtitle="Current classification results."
        >
          <div className="space-y-3">

            {[
              'Fetal brain',
              'Fetal abdomen',
              'Fetal thorax',
              'Fetal femur',
              'Maternal cervix',
              'Other',
            ].map((plane) => {

              const count =
                scans.filter(
                  (scan) =>
                    scan.predicted_plane ===
                    plane
                ).length;

              const percentage =
                scans.length > 0
                  ? (count /
                      scans.length) *
                    100
                  : 0;

              return (
                <div key={plane}>

                  <div className="flex justify-between text-xs">
                    <span className="text-slate-600">
                      {plane}
                    </span>

                    <span className="font-medium text-slate-800">
                      {count}
                    </span>
                  </div>

                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">

                    <div
                      className="h-full rounded-full bg-violet-500"
                      style={{
                        width: `${percentage}%`,
                      }}
                    />

                  </div>

                </div>
              );
            })}

          </div>
        </Card>

        {/* SYSTEM */}

        <Card
          title="System Status"
          subtitle="Current backend connectivity."
        >
          <div className="space-y-3">

            <div className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3">

              <div className="flex items-center gap-3">
                <Server
                  size={18}
                  className="text-slate-500"
                />

                <span className="text-sm font-medium text-slate-700">
                  Backend API
                </span>
              </div>

              <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                  backendStatus === 'Online'
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'bg-amber-50 text-amber-700'
                }`}
              >
                {backendStatus}
              </span>

            </div>

            <div className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3">

              <div className="flex items-center gap-3">
                <Database
                  size={18}
                  className="text-slate-500"
                />

                <span className="text-sm font-medium text-slate-700">
                  Database / Data API
                </span>
              </div>

              <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                  !loading && !error
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'bg-amber-50 text-amber-700'
                }`}
              >
                {!loading && !error
                  ? 'Available'
                  : 'Checking'}
              </span>

            </div>

            <div className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3">

              <div className="flex items-center gap-3">
                <Brain
                  size={18}
                  className="text-slate-500"
                />

                <span className="text-sm font-medium text-slate-700">
                  AI Pipeline
                </span>
              </div>

              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                Ready
              </span>

            </div>

          </div>
        </Card>

      </section>

      {/* DISCLAIMER */}

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
        <div className="flex gap-3">

          <AlertTriangle
            size={18}
            className="mt-0.5 shrink-0 text-amber-700"
          />

          <p className="text-xs leading-5 text-amber-800">
            FetalAI is an AI-assisted research
            and screening prototype. Results
            must be reviewed by a qualified
            healthcare professional and are not
            a clinically validated diagnosis.
          </p>

        </div>
      </div>

    </div>
  );
}

export default DashboardPage;