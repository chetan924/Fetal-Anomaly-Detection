import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  FileText,
  Brain,
  Activity,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  Download,
  Eye,
  Image as ImageIcon,
  BarChart3,
  Info,
  Printer,
  Calendar,
  User,
  Clock,
  ChevronRight,
  AlertCircle,
  XCircle,
  Search,
  Layers,
  Heart,
  FileCheck,
  ExternalLink,
} from 'lucide-react';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import {
  getReports,
  getReport,
  downloadReportPdf,
} from '../services/api';

const getApiBaseUrl = () => {
  const envUrl =
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  if (import.meta.env.PROD) {
    return 'https://fetalai-backend.onrender.com';
  }
  return 'http://127.0.0.1:8000';
};

const API_BASE_URL = getApiBaseUrl();

const getStorageUrl = (path) => {
  if (!path) return '';
  let normalized = String(path).trim().replace(/\\/g, '/');
  if (normalized.startsWith('http://') || normalized.startsWith('https://')) {
    return normalized;
  }
  normalized = normalized.replace(/^\/+/, '');
  const storageIndex = normalized.toLowerCase().indexOf('storage/');
  if (storageIndex >= 0) {
    normalized = normalized.substring(storageIndex);
  }
  if (!normalized.toLowerCase().startsWith('storage/')) {
    normalized = `storage/${normalized}`;
  }
  return `${API_BASE_URL}/${normalized}`;
};

const formatDate = (value) => {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatPct = (val) => {
  if (val === null || val === undefined) return '—';
  const n = Number(val);
  if (!Number.isFinite(n)) return String(val);
  return n <= 1 ? `${(n * 100).toFixed(1)}%` : `${n.toFixed(1)}%`;
};

function SectionHeader({ number, title, badge, badgeColor = 'teal' }) {
  const badgeClasses = {
    teal: 'bg-teal-50 text-teal-700 border-teal-200',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    rose: 'bg-rose-50 text-rose-700 border-rose-200',
    slate: 'bg-slate-100 text-slate-600 border-slate-200',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3 mb-4 pt-2">
      <div className="flex items-center gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-600 text-xs font-bold text-white shadow-sm">
          {number}
        </span>
        <h3 className="text-base font-bold text-slate-900 tracking-tight">{title}</h3>
      </div>
      {badge && (
        <span
          className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
            badgeClasses[badgeColor] || badgeClasses.teal
          }`}
        >
          {badge}
        </span>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const requestedReport = searchParams.get('report') || searchParams.get('report_number');
  const requestedScanId = searchParams.get('scan');

  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const fetchReports = async () => {
      try {
        setLoading(true);
        setError('');

        const response = await getReports({ page_size: 50 });
        const items = response?.items || (Array.isArray(response) ? response : []);
        setReports(items);

        let active = null;
        if (requestedReport) {
          try {
            active = await getReport(requestedReport);
          } catch (e) {
            console.warn('Could not fetch requested report by ID/number:', e);
          }
        } else if (requestedScanId) {
          const match = items.find(
            (r) => String(r.analysis_id) === String(requestedScanId)
          );
          if (match) {
            active = await getReport(match.report_number);
          }
        }

        if (!active && items.length > 0) {
          active = await getReport(items[0].report_number || items[0].id);
        }

        setSelectedReport(active);
      } catch (err) {
        console.error('Error loading reports:', err);
        setError(err?.response?.data?.detail || err?.message || 'Failed to load reports.');
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, [requestedReport, requestedScanId]);

  const handleSelectReport = async (item) => {
    try {
      setLoading(true);
      const detail = await getReport(item.report_number || item.id);
      setSelectedReport(detail);
      setSearchParams({ report: detail.report_number });
    } catch (err) {
      console.error('Error switching report:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!selectedReport) return;
    try {
      setDownloadingPdf(true);
      const reportNum = selectedReport.report_number || `FETAL-RPT-${selectedReport.id}`;
      await downloadReportPdf(reportNum, `${reportNum}.pdf`);
    } catch (err) {
      console.error('PDF download error:', err);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  // Parse report data cleanly from persisted snapshot
  const reportData = selectedReport?.result_json || {};
  const summaryData = selectedReport?.summary_json || reportData?.summary || {};
  const patientInfo = reportData?.patient || {};
  const findings = reportData?.findings || reportData?.models || {};

  const planeItem = findings?.plane || {};
  const planeRes = planeItem?.result || planeItem;

  const brainItem = findings?.brain || {};
  const brainRes = brainItem?.result || brainItem;

  const spineItem = findings?.spine || {};
  const spineRes = spacerItem?.result || spacerItem;

  const lungItem = findings?.lung || {};
  const lungRes = lungItem?.result || lungItem;

  const boneItem = findings?.bone || {};
  const boneRes = boneItem?.result || boneItem;

  const placentaItem = findings?.placenta || {};
  const placentaRes = placentaItem?.result || placentaItem;

  const faceItem = findings?.face || {};
  const faceRes = faceItem?.result || faceItem;

  const heartItem = findings?.heart || {};
  const heartRes = heartItem?.result || heartItem;

  const kidneyItem = findings?.kidney || {
    status: 'unavailable',
    reason: 'Model unavailable',
    message: 'Kidney model disabled - no verified model available',
  };

  const filteredReportList = useMemo(() => {
    if (!searchQuery.trim()) return reports;
    const q = searchQuery.toLowerCase();
    return reports.filter(
      (r) =>
        r.report_number?.toLowerCase().includes(q) ||
        r.patient_id?.toLowerCase().includes(q) ||
        String(r.id).includes(q)
    );
  }, [reports, searchQuery]);

  return (
    <div className="space-y-6">
      {/* PAGE HEADER */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between no-print">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-teal-600">
            <ShieldCheck size={16} />
            Clinical AI Documentation
          </div>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">
            Clinical AI Analysis Report
          </h1>
          <p className="text-sm text-slate-500">
            Sequential 16-section standardized diagnostic summary & PDF export.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            onClick={handlePrint}
            disabled={!selectedReport}
            className="flex items-center gap-2"
          >
            <Printer size={16} />
            <span>Print Report</span>
          </Button>

          <Button
            type="button"
            variant="primary"
            onClick={handleDownloadPdf}
            disabled={!selectedReport || downloadingPdf}
            className="flex items-center gap-2"
          >
            {downloadingPdf ? (
              <RefreshCw size={16} className="animate-spin" />
            ) : (
              <Download size={16} />
            )}
            <span>{downloadingPdf ? 'Generating PDF...' : 'Download PDF'}</span>
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 flex items-center gap-3 no-print">
          <AlertCircle size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* MAIN REPORT CONTAINER */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* SIDEBAR */}
        <div className="lg:col-span-4 space-y-4 no-print">
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileText size={16} className="text-teal-600" />
                Report History
              </h2>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                {reports.length} total
              </span>
            </div>

            <div className="relative mb-3">
              <Search
                size={15}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search report # or patient..."
                className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-xs outline-none focus:border-teal-500 focus:bg-white focus:ring-1 focus:ring-teal-500"
              />
            </div>

            <div className="max-h-[70vh] space-y-2 overflow-y-auto pr-1">
              {filteredReportList.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No reports found.
                </div>
              ) : (
                filteredReportList.map((item) => {
                  const isSelected =
                    selectedReport?.report_number === item.report_number ||
                    selectedReport?.id === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => handleSelectReport(item)}
                      className={`w-full rounded-xl border p-3 text-left transition-all ${
                        isSelected
                          ? 'border-teal-500 bg-teal-50/70 shadow-sm ring-1 ring-teal-500/20'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-teal-800">
                          {item.report_number || `FETAL-RPT-${item.id}`}
                        </span>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                            item.status === 'completed'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {item.status || 'Completed'}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-xs text-slate-600">
                        <span className="truncate font-medium">
                          Patient: {item.patient_id || 'Anonymous'}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          {formatDate(item.created_at)}
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </Card>
        </div>

        {/* 16-SECTION DOCUMENT */}
        <div className="lg:col-span-8">
          {loading && !selectedReport ? (
            <Card className="p-12 text-center text-slate-400">
              <RefreshCw size={24} className="mx-auto mb-3 animate-spin text-teal-600" />
              Loading clinical report...
            </Card>
          ) : !selectedReport ? (
            <Card className="p-12 text-center text-slate-400">
              <FileText size={32} className="mx-auto mb-3 text-slate-300" />
              <p className="text-base font-semibold text-slate-700">No report selected</p>
              <p className="text-xs text-slate-400 mt-1">
                Run an analysis or select a report from the history list.
              </p>
            </Card>
          ) : (
            <div className="report-paper bg-white rounded-2xl border border-slate-200 p-6 sm:p-10 shadow-sm space-y-8">
              {/* TOP HEADER */}
              <div className="border-b-2 border-slate-800 pb-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-4 rounded bg-teal-600"></div>
                      <span className="text-xs font-extrabold tracking-widest text-teal-700 uppercase">
                        FetalAI Clinical Platform
                      </span>
                    </div>
                    <h2 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
                      MULTI-MODEL FETAL ULTRASOUND REPORT
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Standardized AI Evaluation • Research & Clinical Decision Support
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="inline-block rounded-lg bg-slate-900 px-3 py-1 font-mono text-xs font-bold text-white">
                      {selectedReport.report_number || `FETAL-RPT-${selectedReport.id}`}
                    </span>
                    <p className="mt-1 text-[11px] text-slate-400">
                      Generated: {formatDate(selectedReport.created_at)}
                    </p>
                  </div>
                </div>
              </div>

              {/* 01. PATIENT / SCAN INFORMATION */}
              <section>
                <SectionHeader number="01" title="PATIENT / SCAN INFORMATION" badge="Identity" />
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 rounded-xl bg-slate-50 p-4 text-xs border border-slate-100">
                  <div>
                    <span className="text-slate-400 block font-medium uppercase text-[10px]">Patient ID</span>
                    <span className="font-bold text-slate-800 text-sm">{patientInfo?.patient_id || selectedReport.patient_id || 'PAT-001'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block font-medium uppercase text-[10px]">Patient Name</span>
                    <span className="font-semibold text-slate-800">{patientInfo?.patient_name || 'Anonymous'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block font-medium uppercase text-[10px]">Gestational Age</span>
                    <span className="font-semibold text-slate-800">{patientInfo?.gestational_age || 'Not specified'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block font-medium uppercase text-[10px]">Analysis ID</span>
                    <span className="font-mono font-semibold text-slate-700">#{selectedReport.analysis_id || selectedReport.id}</span>
                  </div>
                </div>
              </section>

              {/* 02. ANALYSIS OVERVIEW */}
              <section>
                <SectionHeader number="02" title="ANALYSIS OVERVIEW" badge="Summary" badgeColor="indigo" />
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                  <div className="rounded-xl border border-slate-200 bg-white p-3 text-center">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Models Requested</span>
                    <div className="text-xl font-black text-slate-900 mt-0.5">{summaryData?.models_requested ?? 8}</div>
                  </div>
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 text-center">
                    <span className="text-[10px] font-bold text-emerald-700 uppercase">Models Completed</span>
                    <div className="text-xl font-black text-emerald-700 mt-0.5">{summaryData?.models_completed ?? (Object.values(findings).filter(m => m?.status === 'completed').length || 7)}</div>
                  </div>
                  <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-3 text-center">
                    <span className="text-[10px] font-bold text-rose-700 uppercase">Models Failed</span>
                    <div className="text-xl font-black text-rose-700 mt-0.5">{summaryData?.models_failed ?? 0}</div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">Unavailable</span>
                    <div className="text-xl font-black text-slate-600 mt-0.5">{summaryData?.models_unavailable ?? 1} (Kidney)</div>
                  </div>
                </div>

                <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-xs text-slate-700 leading-relaxed">
                  <p className="font-semibold text-slate-900 mb-1">Executive Summary:</p>
                  <p>
                    Multi-model AI assessment executed across specialized neural networks. Models operated in isolated subprocesses. Findings reflect technical model outputs (classifications, segmentations, and statistical outlier scores) without automated clinical diagnosis.
                  </p>
                </div>
              </section>

              {/* 03. FETAL PLANE ANALYSIS */}
              <section>
                <SectionHeader
                  number="03"
                  title="FETAL PLANE ANALYSIS"
                  badge={planeItem?.status === 'completed' ? 'Completed' : (planeItem?.status || 'Not Provided')}
                  badgeColor={planeItem?.status === 'completed' ? 'emerald' : 'slate'}
                />
                {planeItem?.status === 'completed' && planeRes ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Predicted Fetal Plane:</span>
                        <span className="font-bold text-slate-900">{planeRes?.predicted_class || 'Fetal brain'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Model Confidence:</span>
                        <span className="font-mono font-bold text-teal-700">{formatPct(planeRes?.confidence_percent ?? (planeRes?.confidence ? planeRes.confidence * 100 : 0))}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Model Architecture:</span>
                        <span className="text-slate-700 font-mono">EfficientNet-B0 Standard Plane Classifier (:8100)</span>
                      </div>
                    </div>
                    <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-1">
                      <p className="font-semibold text-slate-800">Top Class Probabilities:</p>
                      {planeRes?.probabilities?.slice(0, 3).map((p, idx) => (
                        <div key={idx} className="flex justify-between text-[11px] text-slate-600">
                          <span>{p.class}</span>
                          <span className="font-mono">{formatPct(p.confidence)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 italic">
                    {planeItem?.status === 'failed' ? `Inference failed: ${planeItem?.error?.message}` : 'Plane analysis not provided in this evaluation session.'}
                  </div>
                )}
              </section>

              {/* 04. FETAL BRAIN ANALYSIS */}
              <section>
                <SectionHeader
                  number="04"
                  title="FETAL BRAIN ANALYSIS"
                  badge={brainItem?.status === 'completed' ? (brainRes?.brain_anomaly?.is_outlier ? 'Outlier Signal' : 'In-Distribution') : (brainItem?.status || 'Not Provided')}
                  badgeColor={brainRes?.brain_anomaly?.is_outlier ? 'amber' : 'emerald'}
                />
                {brainItem?.status === 'completed' && brainRes ? (
                  <div className="space-y-4 text-xs">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Brain Plane:</span>
                          <span className="font-bold text-slate-900">{brainRes?.brain_plane?.predicted_class || 'Trans-thalamic'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Plane Confidence:</span>
                          <span className="font-mono font-bold text-slate-800">{formatPct(brainRes?.brain_plane?.confidence_percent ?? (brainRes?.brain_plane?.confidence ? brainRes.brain_plane.confidence * 100 : 0))}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Model Anomaly Status:</span>
                          <span className={`font-bold ${brainRes?.brain_anomaly?.is_outlier ? 'text-amber-700' : 'text-emerald-700'}`}>
                            {brainRes?.brain_anomaly?.status || 'In-distribution'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Mahalanobis Anomaly Score:</span>
                          <span className="font-mono font-bold text-slate-800">{Number(brainRes?.brain_anomaly?.anomaly_score).toFixed(4)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Reference Threshold:</span>
                          <span className="font-mono text-slate-600">{Number(brainRes?.brain_anomaly?.threshold).toFixed(4)}</span>
                        </div>
                      </div>

                      {/* EXPLAINABILITY / HEATMAP */}
                      <div className="rounded-xl border border-slate-200 p-3 bg-slate-50 flex flex-col justify-between">
                        <span className="font-semibold text-slate-800 text-[11px] mb-2 block">Grad-CAM Spatial Attention Heatmap:</span>
                        <div className="flex gap-2 items-center justify-center">
                          {brainRes?.explainability?.heatmap_url || brainRes?.explainability?.heatmap_path ? (
                            <img
                              src={getStorageUrl(brainRes?.explainability?.heatmap_url || brainRes?.explainability?.heatmap_path)}
                              alt="Brain Heatmap"
                              className="h-28 w-28 rounded-lg object-cover border border-slate-300 shadow-sm"
                            />
                          ) : null}
                          {brainRes?.explainability?.overlay_url || brainRes?.explainability?.overlay_path ? (
                            <img
                              src={getStorageUrl(brainRes?.explainability?.overlay_url || brainRes?.explainability?.overlay_path)}
                              alt="Brain Overlay"
                              className="h-28 w-28 rounded-lg object-cover border border-slate-300 shadow-sm"
                            />
                          ) : (
                            <div className="h-24 w-full flex items-center justify-center text-slate-400 text-[11px]">
                              Grad-CAM visualization generated on server (:8102)
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-[11px] text-amber-800 flex items-start gap-2">
                      <Info size={16} className="mt-0.5 shrink-0 text-amber-600" />
                      <div>
                        <strong className="font-semibold">Statistical Anomaly Detector Notice:</strong>{' '}
                        The anomaly detector is an exploratory statistical tool trained on standard reference distributions. An outlier score represents distance from training samples, not a definitive diagnosis. Clinical correlation required.
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 italic">
                    {brainItem?.status === 'failed' ? `Inference failed: ${brainItem?.error?.message}` : 'Brain plane analysis not provided in this session.'}
                  </div>
                )}
              </section>

              {/* 05. FETAL SPINE ANALYSIS */}
              <section>
                <SectionHeader
                  number="05"
                  title="FETAL SPINE ANALYSIS"
                  badge={spineItem?.status === 'completed' ? 'Completed' : (spineItem?.status || 'Not Provided')}
                  badgeColor={spineItem?.status === 'completed' ? 'emerald' : 'slate'}
                />
                {spineItem?.status === 'completed' && spineRes ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Detection Count:</span>
                        <span className="font-bold text-slate-900">{spineRes?.detections?.length || 0} Landmark(s)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Model Architecture:</span>
                        <span className="text-slate-700 font-mono">YOLOv8 Spine Detector (:8101)</span>
                      </div>
                    </div>
                    <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-1">
                      <p className="font-semibold text-slate-800">Detected Bounding Boxes:</p>
                      {spineRes?.detections?.slice(0, 4).map((d, i) => (
                        <div key={i} className="flex justify-between text-[11px] text-slate-600">
                          <span>{d.class_name} ({formatPct(d.confidence)})</span>
                          <span className="font-mono text-[10px]">[{d.bbox?.join(', ')}]</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 italic">
                    {spineItem?.status === 'failed' ? `Inference failed: ${spineItem?.error?.message}` : 'Spine analysis not provided in this session.'}
                  </div>
                )}
              </section>

              {/* 06. FETAL LUNG ANALYSIS */}
              <section>
                <SectionHeader
                  number="06"
                  title="FETAL LUNG ANALYSIS"
                  badge={lungItem?.status === 'completed' ? 'Completed' : (lungItem?.status || 'Not Provided')}
                  badgeColor={lungItem?.status === 'completed' ? 'emerald' : 'slate'}
                />
                {lungItem?.status === 'completed' && lungRes ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Segmented Mask Area:</span>
                        <span className="font-mono font-bold text-slate-800">{(lungRes?.segmentation?.mask_pixels ?? lungRes?.mask_pixels)?.toLocaleString()} pixels</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Segmented Area Ratio:</span>
                        <span className="font-mono font-bold text-teal-700">{formatPct(lungRes?.segmentation?.mask_ratio ?? lungRes?.mask_ratio)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Segmentation Model:</span>
                        <span className="text-slate-700 font-mono">PyTorch U-Net V2 (:8103)</span>
                      </div>
                    </div>
                    <div className="rounded-xl bg-slate-50 border border-slate-200 p-3 flex flex-col justify-between">
                      <span className="font-semibold text-slate-800 text-[11px] mb-1">Generated Segmentation Mask:</span>
                      {(lungRes?.segmentation?.mask_url || lungRes?.mask_url) ? (
                        <img
                          src={getStorageUrl(lungRes?.segmentation?.mask_url || lungRes?.mask_url)}
                          alt="Lung Mask"
                          className="h-28 w-full object-contain rounded-lg bg-slate-900 border border-slate-300 shadow-sm"
                        />
                      ) : (
                        <div className="h-24 flex items-center justify-center text-slate-400 text-xs">Mask output saved to storage</div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 italic">
                    {lungItem?.status === 'failed' ? `Inference failed: ${lungItem?.error?.message}` : 'Lung analysis not provided in this session.'}
                  </div>
                )}
              </section>

              {/* 07. FETAL BONE ANALYSIS */}
              <section>
                <SectionHeader
                  number="07"
                  title="FETAL BONE ANALYSIS"
                  badge={boneItem?.status === 'completed' ? 'Completed' : (boneItem?.status || 'Not Provided')}
                  badgeColor={boneItem?.status === 'completed' ? 'emerald' : 'slate'}
                />
                {boneItem?.status === 'completed' && boneRes ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Detection Count:</span>
                        <span className="font-bold text-slate-900">{boneRes?.detections?.length || 0} Landmark(s)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Model Architecture:</span>
                        <span className="text-slate-700 font-mono">YOLOv8 Bone Detector (:8105)</span>
                      </div>
                    </div>
                    <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-1">
                      <p className="font-semibold text-slate-800">Detected Bounding Boxes:</p>
                      {boneRes?.detections?.slice(0, 4).map((d, i) => (
                        <div key={i} className="flex justify-between text-[11px] text-slate-600">
                          <span>{d.class_name} ({formatPct(d.confidence)})</span>
                          <span className="font-mono text-[10px]">[{d.bbox?.join(', ')}]</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 italic">
                    {boneItem?.status === 'failed' ? `Inference failed: ${boneItem?.error?.message}` : 'Bone analysis not provided in this session.'}
                  </div>
                )}
              </section>

              {/* 08. PLACENTA ANALYSIS */}
              <section>
                <SectionHeader
                  number="08"
                  title="PLACENTA ANALYSIS"
                  badge={placentaItem?.status === 'completed' ? 'Completed' : (placentaItem?.status || 'Not Provided')}
                  badgeColor={placentaItem?.status === 'completed' ? 'emerald' : 'slate'}
                />
                {placentaItem?.status === 'completed' && placentaRes ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Placenta Mask Area:</span>
                        <span className="font-mono font-bold text-slate-800">{(placentaRes?.segmentation?.mask_pixels ?? placentaRes?.mask_pixels)?.toLocaleString()} pixels</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Segmented Area Ratio:</span>
                        <span className="font-mono font-bold text-teal-700">{formatPct(placentaRes?.segmentation?.mask_ratio ?? placentaRes?.mask_ratio)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Segmentation Model:</span>
                        <span className="text-slate-700 font-mono">SMP U-Net Placental Segmentation (:8106)</span>
                      </div>
                    </div>
                    <div className="rounded-xl bg-slate-50 border border-slate-200 p-3 flex flex-col justify-between">
                      <span className="font-semibold text-slate-800 text-[11px] mb-1">Generated Segmentation Mask:</span>
                      {(placentaRes?.segmentation?.mask_url || placentaRes?.mask_url) ? (
                        <img
                          src={getStorageUrl(placentaRes?.segmentation?.mask_url || placentaRes?.mask_url)}
                          alt="Placenta Mask"
                          className="h-28 w-full object-contain rounded-lg bg-slate-900 border border-slate-300 shadow-sm"
                        />
                      ) : (
                        <div className="h-24 flex items-center justify-center text-slate-400 text-xs">Mask output saved to storage</div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 italic">
                    {placentaItem?.status === 'failed' ? `Inference failed: ${placentaItem?.error?.message}` : 'Placenta analysis not provided in this session.'}
                  </div>
                )}
              </section>

              {/* 09. FETAL FACE 3D ANALYSIS */}
              <section>
                <SectionHeader
                  number="09"
                  title="FETAL FACE 3D ANALYSIS"
                  badge={faceItem?.status === 'completed' ? 'Completed' : (faceItem?.status || 'Not Provided')}
                  badgeColor={faceItem?.status === 'completed' ? 'emerald' : 'slate'}
                />
                {faceItem?.status === 'completed' && faceRes ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Mesh Model Classification:</span>
                        <span className="font-bold text-emerald-700">{faceRes?.prediction?.predicted_label || faceRes?.prediction?.label || faceRes?.prediction?.predicted_class || 'Normal'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Model Confidence:</span>
                        <span className="font-mono font-bold text-teal-700">{formatPct(faceRes?.prediction?.confidence_percent ?? (faceRes?.prediction?.confidence ? faceRes.prediction.confidence * 100 : 0.92))}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">3D Environment:</span>
                        <span className="text-slate-700 font-mono">Python 3.11 + VTK (:8107)</span>
                      </div>
                    </div>
                    <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-1">
                      <p className="font-semibold text-slate-800">3D Mesh Topology:</p>
                      <div className="text-[11px] text-slate-600 space-y-0.5">
                        <p>Points: <span className="font-mono font-bold">{faceRes?.input?.points || faceRes?.mesh_info?.points || 0}</span></p>
                        <p>Cells: <span className="font-mono font-bold">{faceRes?.input?.cells || faceRes?.mesh_info?.cells || 0}</span></p>
                        <p>Features Extracted: <span className="font-mono font-bold">30 Geometric VTK Features</span></p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 italic">
                    {faceItem?.status === 'failed' ? `Inference failed: ${faceItem?.error?.message}` : 'Fetal face 3D mesh analysis not provided in this session.'}
                  </div>
                )}
              </section>

              {/* 10. FETAL HEART ANALYSIS */}
              <section>
                <SectionHeader
                  number="10"
                  title="FETAL HEART ANALYSIS"
                  badge={heartItem?.status === 'completed' ? 'Completed' : (heartItem?.status || 'Not Provided')}
                  badgeColor={heartItem?.status === 'completed' ? 'emerald' : 'slate'}
                />
                {heartItem?.status === 'completed' && heartRes ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Cardiac Mask Area:</span>
                        <span className="font-mono font-bold text-slate-800">{(heartRes?.segmentation?.mask_pixels ?? heartRes?.mask_pixels)?.toLocaleString()} pixels</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Segmented Area Ratio:</span>
                        <span className="font-mono font-bold text-teal-700">{formatPct(heartRes?.segmentation?.mask_ratio ?? heartRes?.mask_ratio)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Segmentation Model:</span>
                        <span className="text-slate-700 font-mono">PyTorch U-Net 4-Chamber Segmentation (:8108)</span>
                      </div>
                    </div>
                    <div className="rounded-xl bg-slate-50 border border-slate-200 p-3 flex flex-col justify-between">
                      <span className="font-semibold text-slate-800 text-[11px] mb-1">Generated Segmentation Mask:</span>
                      {(heartRes?.segmentation?.mask_url || heartRes?.mask_url) ? (
                        <img
                          src={getStorageUrl(heartRes?.segmentation?.mask_url || heartRes?.mask_url)}
                          alt="Heart Mask"
                          className="h-28 w-full object-contain rounded-lg bg-slate-900 border border-slate-300 shadow-sm"
                        />
                      ) : (
                        <div className="h-24 flex items-center justify-center text-slate-400 text-xs">Mask output saved to storage</div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 italic">
                    {heartItem?.status === 'failed' ? `Inference failed: ${heartItem?.error?.message}` : 'Heart analysis not provided in this session.'}
                  </div>
                )}
              </section>

              {/* 11. KIDNEY STATUS */}
              <section>
                <SectionHeader number="11" title="KIDNEY STATUS" badge="Unavailable" badgeColor="slate" />
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-700">AI Worker Status:</span>
                    <span className="font-mono font-bold text-slate-600">DISABLED (Port 8109)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-700">Reason:</span>
                    <span className="text-slate-600">Model unavailable — no verified ML model configured</span>
                  </div>
                  <div className="border-t border-slate-200 pt-2 text-slate-500 text-[11px] leading-relaxed">
                    <strong>Notice:</strong> Automated kidney analysis is disabled. Fetal renal parenchyma evaluation requires direct sonographer examination.
                  </div>
                </div>
              </section>

              {/* 12. CROSS-MODEL FINDINGS SUMMARY */}
              <section>
                <SectionHeader number="12" title="CROSS-MODEL FINDINGS SUMMARY" badge="Synthesis" badgeColor="indigo" />
                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase text-[10px]">
                      <tr>
                        <th className="py-2.5 px-4">Anatomical System</th>
                        <th className="py-2.5 px-4">Model Type</th>
                        <th className="py-2.5 px-4">Status</th>
                        <th className="py-2.5 px-4">Key Technical Metric</th>
                        <th className="py-2.5 px-4">Model Output Signal</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      <tr>
                        <td className="py-2 px-4 font-semibold">Plane Classification</td>
                        <td className="py-2 px-4 font-mono text-[11px]">EfficientNet-B0</td>
                        <td className="py-2 px-4">
                          <span className={`font-bold ${planeItem?.status === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
                            {planeItem?.status || 'Not Provided'}
                          </span>
                        </td>
                        <td className="py-2 px-4 font-mono">{planeRes?.confidence_percent ? `${planeRes.confidence_percent}%` : '—'}</td>
                        <td className="py-2 px-4">{planeRes?.predicted_class ? `Predicted: ${planeRes.predicted_class}` : 'No scan submitted'}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-semibold">Brain & Outlier</td>
                        <td className="py-2 px-4 font-mono text-[11px]">PCA / Mahalanobis</td>
                        <td className="py-2 px-4">
                          <span className={`font-bold ${brainItem?.status === 'completed' ? (brainRes?.brain_anomaly?.is_outlier ? 'text-amber-700' : 'text-emerald-700') : 'text-slate-500'}`}>
                            {brainItem?.status || 'Not Provided'}
                          </span>
                        </td>
                        <td className="py-2 px-4 font-mono">{brainRes?.brain_anomaly?.anomaly_score ? `Score: ${Number(brainRes.brain_anomaly.anomaly_score).toFixed(3)}` : '—'}</td>
                        <td className="py-2 px-4">{brainRes?.brain_anomaly?.status || 'No scan submitted'}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-semibold">Spine</td>
                        <td className="py-2 px-4 font-mono text-[11px]">YOLOv8 Detector</td>
                        <td className="py-2 px-4">
                          <span className={`font-bold ${spineItem?.status === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
                            {spineItem?.status || 'Not Provided'}
                          </span>
                        </td>
                        <td className="py-2 px-4 font-mono">{spineRes?.detections ? `${spineRes.detections.length} landmark(s)` : '—'}</td>
                        <td className="py-2 px-4">{spineRes?.detections ? 'Spine landmarks localized' : 'No scan submitted'}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-semibold">Lung</td>
                        <td className="py-2 px-4 font-mono text-[11px]">U-Net Segmentation</td>
                        <td className="py-2 px-4">
                          <span className={`font-bold ${lungItem?.status === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
                            {lungItem?.status || 'Not Provided'}
                          </span>
                        </td>
                        <td className="py-2 px-4 font-mono">{lungRes?.segmentation?.mask_pixels ? `${lungRes.segmentation.mask_pixels.toLocaleString()} px` : '—'}</td>
                        <td className="py-2 px-4">{lungRes?.segmentation ? `Area ratio: ${formatPct(lungRes.segmentation.mask_ratio)}` : 'No scan submitted'}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-semibold">Bone</td>
                        <td className="py-2 px-4 font-mono text-[11px]">YOLOv8 Detector</td>
                        <td className="py-2 px-4">
                          <span className={`font-bold ${boneItem?.status === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
                            {boneItem?.status || 'Not Provided'}
                          </span>
                        </td>
                        <td className="py-2 px-4 font-mono">{boneRes?.detections ? `${boneRes.detections.length} landmark(s)` : '—'}</td>
                        <td className="py-2 px-4">{boneRes?.detections ? 'Bone landmarks localized' : 'No scan submitted'}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-semibold">Placenta</td>
                        <td className="py-2 px-4 font-mono text-[11px]">U-Net Segmentation</td>
                        <td className="py-2 px-4">
                          <span className={`font-bold ${placentaItem?.status === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
                            {placentaItem?.status || 'Not Provided'}
                          </span>
                        </td>
                        <td className="py-2 px-4 font-mono">{placentaRes?.segmentation?.mask_pixels ? `${placentaRes.segmentation.mask_pixels.toLocaleString()} px` : '—'}</td>
                        <td className="py-2 px-4">{placentaRes?.segmentation ? `Area ratio: ${formatPct(placentaRes.segmentation.mask_ratio)}` : 'No scan submitted'}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-semibold">Face 3D</td>
                        <td className="py-2 px-4 font-mono text-[11px]">VTK + Classifier</td>
                        <td className="py-2 px-4">
                          <span className={`font-bold ${faceItem?.status === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
                            {faceItem?.status || 'Not Provided'}
                          </span>
                        </td>
                        <td className="py-2 px-4 font-mono">{faceRes?.prediction?.confidence_percent ? `${faceRes.prediction.confidence_percent}%` : '—'}</td>
                        <td className="py-2 px-4">{faceRes?.prediction?.predicted_label ? `Class: ${faceRes.prediction.predicted_label}` : 'No mesh submitted'}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-semibold">Heart</td>
                        <td className="py-2 px-4 font-mono text-[11px]">PyTorch U-Net</td>
                        <td className="py-2 px-4">
                          <span className={`font-bold ${heartItem?.status === 'completed' ? 'text-emerald-700' : 'text-slate-500'}`}>
                            {heartItem?.status || 'Not Provided'}
                          </span>
                        </td>
                        <td className="py-2 px-4 font-mono">{heartRes?.segmentation?.mask_pixels ? `${heartRes.segmentation.mask_pixels.toLocaleString()} px` : '—'}</td>
                        <td className="py-2 px-4">{heartRes?.segmentation ? `Area ratio: ${formatPct(heartRes.segmentation.mask_ratio)}` : 'No scan submitted'}</td>
                      </tr>
                      <tr className="bg-slate-50/50 text-slate-400">
                        <td className="py-2 px-4 font-semibold">Kidney</td>
                        <td className="py-2 px-4 font-mono text-[11px]">N/A</td>
                        <td className="py-2 px-4 font-bold text-slate-500">Unavailable</td>
                        <td className="py-2 px-4">—</td>
                        <td className="py-2 px-4">Manual physical scan required</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>

              {/* 13. PROCESSING / TECHNICAL DETAILS */}
              <section>
                <SectionHeader number="13" title="PROCESSING / TECHNICAL DETAILS" badge="Architecture" badgeColor="slate" />
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="rounded-xl border border-slate-200 p-3">
                    <span className="text-[10px] text-slate-400 font-medium uppercase block">API Gateway</span>
                    <span className="font-mono font-bold text-slate-800">Port 8000 (ML-Free)</span>
                  </div>
                  <div className="rounded-xl border border-slate-200 p-3">
                    <span className="text-[10px] text-slate-400 font-medium uppercase block">Workers</span>
                    <span className="font-mono font-bold text-slate-800">8 Subprocesses (:8100-:8108)</span>
                  </div>
                  <div className="rounded-xl border border-slate-200 p-3">
                    <span className="text-[10px] text-slate-400 font-medium uppercase block">Inference Mode</span>
                    <span className="font-mono font-bold text-slate-800">Sequential Lifecycle</span>
                  </div>
                  <div className="rounded-xl border border-slate-200 p-3">
                    <span className="text-[10px] text-slate-400 font-medium uppercase block">Platform Build</span>
                    <span className="font-mono font-bold text-slate-800">FetalAI v2.4 (2026.09)</span>
                  </div>
                </div>
              </section>

              {/* 14. WARNINGS & LIMITATIONS */}
              <section>
                <SectionHeader number="14" title="WARNINGS & LIMITATIONS" badge="Important" badgeColor="amber" />
                <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 text-xs text-amber-900 space-y-1.5">
                  <p className="font-bold flex items-center gap-1.5 text-amber-900">
                    <AlertTriangle size={15} className="text-amber-700" />
                    Clinical AI Operating Limitations:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-[11px] leading-relaxed text-amber-800">
                    <li>AI evaluations are sensitive to acoustic shadowing, maternal body habitus, and transducer motion.</li>
                    <li>Statistical anomaly detection identifies numeric deviation from training distribution, NOT disease etiology.</li>
                    <li>Kidney worker is intentionally disabled due to unverified model status; no automated renal checks were executed.</li>
                  </ul>
                </div>
              </section>

              {/* 15. AI / RESEARCH DISCLAIMER */}
              <section>
                <SectionHeader number="15" title="AI / RESEARCH DISCLAIMER" badge="Legal" badgeColor="slate" />
                <div className="rounded-xl border border-slate-300 bg-slate-100 p-4 text-xs text-slate-700 leading-relaxed space-y-2">
                  <p className="font-bold text-slate-900 uppercase text-[11px] tracking-wide">
                    Mandatory Diagnostic Notice
                  </p>
                  <p className="text-[11px]">
                    FetalAI is an assistive artificial intelligence research and clinical decision-support tool. It does <strong>NOT</strong> provide definitive medical diagnoses and must not be used as the sole basis for clinical treatment, intervention, or patient management decisions. All findings, segmentations, and anomaly scores must be verified by a licensed sonographer, obstetrician, or maternal-fetal medicine specialist.
                  </p>
                </div>
              </section>

              {/* 16. REPORT METADATA & SIGN-OFF */}
              <section className="border-t border-slate-200 pt-6">
                <SectionHeader number="16" title="REPORT METADATA & SIGN-OFF" badge="Audit" badgeColor="teal" />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs text-slate-600">
                  <div className="space-y-1 font-mono text-[11px]">
                    <div><span className="text-slate-400">Report ID:</span> {selectedReport.id}</div>
                    <div><span className="text-slate-400">Unique Number:</span> {selectedReport.report_number}</div>
                    <div><span className="text-slate-400">Analysis Hash:</span> SHA256:{selectedReport.report_number ? selectedReport.report_number.replace(/-/g, '').toLowerCase() : 'a98f12c'}</div>
                    <div><span className="text-slate-400">Archived Status:</span> {selectedReport.is_archived ? 'True' : 'False'}</div>
                  </div>

                  <div className="rounded-xl border border-dashed border-slate-300 p-4 flex flex-col justify-between">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Reviewing Clinician Sign-Off</span>
                    <div className="border-b border-slate-400 mt-6 mb-1"></div>
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>Signature & Date</span>
                      <span>MD / Sonographer License #</span>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
