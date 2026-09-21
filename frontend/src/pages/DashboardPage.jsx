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
  getReports,
  healthCheck,
} from '../services/api';

const statIcons = {
  'Total Scans': ScanLine,
  'Completed Scans': CheckCircle2,
  'Statistical Outliers': AlertTriangle,
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
  const [reports, setReports] = useState([]);
  const [backendStatus, setBackendStatus] = useState('Checking...');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError('');

      const [patientsResult, scansResult, reportsResult] =
        await Promise.all([
          getPatients().catch(() => []),
          getScans().catch(() => []),
          getReports({ page_size: 10 }).catch(() => ({ items: [] })),
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

      setReports(
        reportsResult?.items || (Array.isArray(reportsResult) ? reportsResult : [])
      );

      setBackendStatus('Online');

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

    const completedScans = totalScans;

    return {
      totalScans,
      brainScans,
      flaggedScans,
      completedScans,
      patients: patients.length,
      reportsCount: reports.length,
    };
  }, [patients, scans, reports]);

  const recentScans = useMemo(() => {
    return [...scans]
      .sort(
        (a, b) =>
          new Date(b.created_at || 0) -
          new Date(a.created_at || 0)
      )
      .slice(0, 5);
  }, [scans]);

  return (
    <div className="space-y-8">
      {/* PAGE HEADER */}
      <PageHeader
        title="Clinical Dashboard"
        subtitle="Multi-Model Fetal Ultrasound AI Inference & Diagnostic Archive Overview"
        badge={
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
              backendStatus === 'Online'
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-red-50 text-red-700'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus === 'Online'
                  ? 'bg-emerald-500'
                  : 'bg-red-500'
              }`}
            />
            Gateway {backendStatus}
          </span>
        }
      />

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* STATS GRID */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Scans</span>
            <div className="rounded-xl bg-cyan-50 p-2.5 text-cyan-700">
              <ScanLine size={20} />
            </div>
          </div>
          <div className="mt-3 text-2xl font-black text-slate-900">{statistics.totalScans}</div>
          <p className="mt-1 text-xs text-slate-400">Processed in system</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Completed Analyses</span>
            <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700">
              <CheckCircle2 size={20} />
            </div>
          </div>
          <div className="mt-3 text-2xl font-black text-slate-900">{statistics.completedScans}</div>
          <p className="mt-1 text-xs text-slate-400">Successful inference runs</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Statistical Outliers</span>
            <div className="rounded-xl bg-amber-50 p-2.5 text-amber-700">
              <AlertTriangle size={20} />
            </div>
          </div>
          <div className="mt-3 text-2xl font-black text-slate-900">{statistics.flaggedScans}</div>
          <p className="mt-1 text-xs text-slate-400">Brain outlier signals flagged</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Patients</span>
            <div className="rounded-xl bg-purple-50 p-2.5 text-purple-700">
              <Users size={20} />
            </div>
          </div>
          <div className="mt-3 text-2xl font-black text-slate-900">{statistics.patients}</div>
          <p className="mt-1 text-xs text-slate-400">Registered clinical records</p>
        </Card>
      </div>

      {/* QUICK ACTIONS & RECENT REPORTS */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-1" title="Quick Actions">
          <div className="mt-4 space-y-3">
            <Button
              type="button"
              variant="primary"
              className="w-full justify-start py-3"
              onClick={() => navigate('/scans/new')}
            >
              <Upload size={18} className="mr-2" />
              New Multi-Model Scan
            </Button>

            <Button
              type="button"
              variant="secondary"
              className="w-full justify-start py-3"
              onClick={() => navigate('/reports')}
            >
              <FileText size={18} className="mr-2" />
              View Clinical Reports
            </Button>

            <Button
              type="button"
              variant="outline"
              className="w-full justify-start py-3"
              onClick={() => navigate('/history')}
            >
              <Activity size={18} className="mr-2" />
              Scan & Report History
            </Button>
          </div>
        </Card>

        <Card className="p-6 lg:col-span-2" title="Recent Clinical Reports" subtitle="Sequential immutable report archives">
          <div className="mt-4 space-y-3">
            {reports.length === 0 ? (
              <p className="py-8 text-center text-xs text-slate-400">No reports generated yet.</p>
            ) : (
              reports.slice(0, 5).map((r) => (
                <div
                  key={r.id}
                  onClick={() => navigate(`/reports?report=${encodeURIComponent(r.report_number || `FETAL-RPT-${r.id}`)}`)}
                  className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-200 bg-white p-3.5 transition hover:border-teal-500 hover:bg-slate-50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
                      <FileText size={18} />
                    </div>
                    <div>
                      <p className="font-mono text-xs font-bold text-slate-900">{r.report_number || `FETAL-RPT-${r.id}`}</p>
                      <p className="text-[11px] text-slate-500">Patient: {r.patient_id || 'Anonymous'}</p>
                    </div>
                  </div>

                  <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-[10px] font-bold text-emerald-700 uppercase">
                    {r.status || 'Completed'}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

export default DashboardPage;
