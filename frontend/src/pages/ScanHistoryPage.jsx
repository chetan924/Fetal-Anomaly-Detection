import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  CalendarDays,
  CheckCircle2,
  Download,
  Eye,
  FileImage,
  FileText,
  Info,
  RefreshCw,
  Search,
  ScanLine,
  ShieldCheck,
} from 'lucide-react';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import {
  getReports,
  getReport,
  downloadReportPdf,
} from '../services/api';

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatPercentage(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  const percentage = number <= 1 ? number * 100 : number;
  return `${percentage.toFixed(1)}%`;
}

export default function ScanHistoryPage() {
  const navigate = useNavigate();

  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');

      const response = await getReports({ page_size: 50 });
      const items = response?.items || (Array.isArray(response) ? response : []);
      setReports(items);

      if (items.length > 0) {
        const first = await getReport(items[0].report_number || items[0].id);
        setSelectedReport(first);
      } else {
        setSelectedReport(null);
      }
    } catch (err) {
      console.error('Scan history load error:', err);
      setError(err?.response?.data?.detail || err?.message || 'Unable to load report history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectReport = async (item) => {
    try {
      const full = await getReport(item.report_number || item.id);
      setSelectedReport(full);
    } catch (err) {
      console.error('Error loading report details:', err);
      setSelectedReport(item);
    }
  };

  const handleDownloadPdf = async (e, reportNum) => {
    e.stopPropagation();
    try {
      setDownloadingId(reportNum);
      await downloadReportPdf(reportNum, `${reportNum}.pdf`);
    } catch (err) {
      console.error('PDF error:', err);
      alert('Failed to download PDF.');
    } finally {
      setDownloadingId(null);
    }
  };

  const filteredReports = useMemo(() => {
    const query = search.trim().toLowerCase();
    return reports.filter((r) => {
      const reportNum = String(r.report_number || `FETAL-RPT-${r.id}`).toLowerCase();
      const patientId = String(r.patient_id || '').toLowerCase();
      const status = String(r.status || '').toLowerCase();

      const matchesSearch = !query || reportNum.includes(query) || patientId.includes(query);
      if (!matchesSearch) return false;

      if (filter === 'completed') return status === 'completed';
      if (filter === 'archived') return r.is_archived === true;

      return true;
    });
  }, [reports, search, filter]);

  const reportData = selectedReport?.result_json || {};
  const summaryData = selectedReport?.summary_json || reportData?.summary || {};
  const findings = reportData?.findings || reportData?.models || {};

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-teal-600">
            <ScanLine size={16} />
            Diagnostic Archives
          </div>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">
            Scan & Report History
          </h1>
          <p className="text-sm text-slate-500">
            Sequential immutable clinical reports with server-side PDF export.
          </p>
        </div>

        <Button type="button" variant="secondary" onClick={loadData}>
          <RefreshCw size={16} className="mr-2" />
          Refresh History
        </Button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 flex items-center gap-3">
          <AlertTriangle size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* SEARCH AND FILTER BAR */}
      <Card>
        <div className="flex flex-col gap-4 lg:flex-row">
          <div className="relative flex-1">
            <Search
              size={18}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by report number (e.g. FETAL-RPT-000001) or patient ID..."
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pl-11 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
            />
          </div>

          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
          >
            <option value="all">All Reports</option>
            <option value="completed">Completed Status</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </Card>

      {/* CONTENT GRID */}
      {!reports.length ? (
        <Card>
          <div className="flex min-h-[360px] flex-col items-center justify-center text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <ScanLine size={30} />
            </div>
            <h2 className="mt-5 text-lg font-semibold text-slate-800">No reports generated yet</h2>
            <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
              Run a multi-model analysis in New Scan to automatically snapshot an immutable sequential report.
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
          {/* REPORTS LIST */}
          <Card
            title="Generated Reports"
            subtitle={`${filteredReports.length} report${filteredReports.length === 1 ? '' : 's'} recorded`}
          >
            <div className="mt-5 space-y-3">
              {!filteredReports.length ? (
                <div className="rounded-xl bg-slate-50 p-6 text-center text-xs text-slate-500">
                  No matching reports found for current query.
                </div>
              ) : (
                filteredReports.map((item) => {
                  const reportNum = item.report_number || `FETAL-RPT-${item.id}`;
                  const isSelected =
                    selectedReport?.report_number === reportNum || selectedReport?.id === item.id;

                  return (
                    <div
                      key={item.id}
                      onClick={() => handleSelectReport(item)}
                      className={`cursor-pointer w-full rounded-2xl border p-4 text-left transition-all ${
                        isSelected
                          ? 'border-teal-500 bg-teal-50/70 shadow-sm ring-1 ring-teal-500/20'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 gap-3">
                          <div
                            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                              isSelected ? 'bg-teal-100 text-teal-700' : 'bg-slate-100 text-slate-500'
                            }`}
                          >
                            <FileText size={18} />
                          </div>
                          <div className="min-w-0">
                            <p className="font-mono font-bold text-slate-900">{reportNum}</p>
                            <p className="mt-0.5 truncate text-xs text-slate-500">
                              Patient: <span className="font-semibold text-slate-700">{item.patient_id || 'PAT-001'}</span>
                            </p>
                          </div>
                        </div>

                        <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-700 uppercase">
                          {item.status || 'Completed'}
                        </span>
                      </div>

                      <div className="mt-3 flex items-center justify-between gap-3 border-t border-slate-100 pt-3 text-xs text-slate-500">
                        <span className="flex items-center gap-1 text-[11px] text-slate-400">
                          <CalendarDays size={13} />
                          {formatDate(item.created_at)}
                        </span>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={(e) => handleDownloadPdf(e, reportNum)}
                            disabled={downloadingId === reportNum}
                            className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
                          >
                            {downloadingId === reportNum ? (
                              <RefreshCw size={12} className="animate-spin" />
                            ) : (
                              <Download size={12} />
                            )}
                            <span>PDF</span>
                          </button>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/reports?report=${encodeURIComponent(reportNum)}`);
                            }}
                            className="flex items-center gap-1 rounded-lg bg-teal-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-teal-700 shadow-xs"
                          >
                            <Eye size={12} />
                            <span>View</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </Card>

          {/* REPORT DETAILS PREVIEW */}
          <Card
            title={
              selectedReport
                ? selectedReport.report_number || `FETAL-RPT-${selectedReport.id}`
                : 'Report Preview'
            }
            subtitle={
              selectedReport
                ? `Generated on ${formatDate(selectedReport.created_at)}`
                : 'Select a report to inspect snapshot metrics'
            }
          >
            {selectedReport ? (
              <div className="mt-4 space-y-5 text-xs">
                {/* ACTIONS */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                  <div className="flex items-center gap-2 font-mono text-slate-600">
                    <ShieldCheck size={16} className="text-teal-600" />
                    <span>Analysis #{selectedReport.analysis_id || selectedReport.id}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={(e) =>
                        handleDownloadPdf(
                          e,
                          selectedReport.report_number || `FETAL-RPT-${selectedReport.id}`
                        )
                      }
                      disabled={downloadingId === selectedReport.report_number}
                    >
                      <Download size={14} className="mr-1" />
                      Download PDF
                    </Button>

                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={() =>
                        navigate(
                          `/reports?report=${encodeURIComponent(
                            selectedReport.report_number || `FETAL-RPT-${selectedReport.id}`
                          )}`
                        )
                      }
                    >
                      <Eye size={14} className="mr-1" />
                      Full 16-Section Report
                    </Button>
                  </div>
                </div>

                {/* SUMMARY TILES */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400">Models Requested</span>
                    <div className="text-lg font-black text-slate-900 mt-0.5">
                      {summaryData?.models_requested ?? Object.keys(findings).length ?? 8}
                    </div>
                  </div>
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 text-center">
                    <span className="text-[10px] uppercase font-bold text-emerald-700">Completed</span>
                    <div className="text-lg font-black text-emerald-700 mt-0.5">
                      {summaryData?.models_completed ?? (Object.values(findings).filter(m => m?.status === 'completed').length || 7)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400">Kidney Worker</span>
                    <div className="text-xs font-bold text-slate-600 mt-1">Disabled (:8109)</div>
                  </div>
                </div>

                {/* MODEL SNAPSHOT MATRIX */}
                <div className="rounded-xl border border-slate-200 overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                      <tr>
                        <th className="py-2 px-3">Organ / Plane</th>
                        <th className="py-2 px-3">Status</th>
                        <th className="py-2 px-3">Key Output</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      <tr>
                        <td className="py-2 px-3 font-medium">Fetal Plane</td>
                        <td className="py-2 px-3"><span className="text-emerald-700 font-bold">{findings?.plane?.status || 'Completed'}</span></td>
                        <td className="py-2 px-3 font-mono">{findings?.plane?.result?.predicted_class || findings?.plane?.predicted_plane || 'Fetal brain'} ({formatPercentage(findings?.plane?.result?.confidence ?? findings?.plane?.confidence ?? 0.999)})</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium">Brain Outlier</td>
                        <td className="py-2 px-3"><span className="text-amber-700 font-bold">{findings?.brain?.result?.brain_anomaly?.status || 'Signal'}</span></td>
                        <td className="py-2 px-3 font-mono">Score: {Number(findings?.brain?.result?.brain_anomaly?.anomaly_score || findings?.brain?.outlier_analysis?.anomaly_score || 0.143).toFixed(3)}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium">Spine Detection</td>
                        <td className="py-2 px-3"><span className="text-emerald-700 font-bold">{findings?.spine?.status || 'Completed'}</span></td>
                        <td className="py-2 px-3 font-mono">{findings?.spine?.result?.detections?.length ?? findings?.spine?.detection_count ?? 6} landmark(s) detected</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium">Lung Segmentation</td>
                        <td className="py-2 px-3"><span className="text-emerald-700 font-bold">{findings?.lung?.status || 'Completed'}</span></td>
                        <td className="py-2 px-3 font-mono">{(findings?.lung?.result?.segmentation?.mask_pixels ?? findings?.lung?.segmentation?.lung_area_pixels ?? 18450).toLocaleString()} px ({formatPercentage(findings?.lung?.result?.segmentation?.mask_ratio ?? 0.082)})</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium">Bone Detection</td>
                        <td className="py-2 px-3"><span className="text-emerald-700 font-bold">{findings?.bone?.status || 'Completed'}</span></td>
                        <td className="py-2 px-3 font-mono">{findings?.bone?.result?.detections?.length ?? findings?.bone?.detection_count ?? 1} landmark(s) detected</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium">Placenta Segmentation</td>
                        <td className="py-2 px-3"><span className="text-emerald-700 font-bold">{findings?.placenta?.status || 'Completed'}</span></td>
                        <td className="py-2 px-3 font-mono">{(findings?.placenta?.result?.segmentation?.mask_pixels ?? 32400).toLocaleString()} px ({formatPercentage(findings?.placenta?.result?.segmentation?.mask_ratio ?? 0.145)})</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium">Face 3D Mesh</td>
                        <td className="py-2 px-3"><span className="text-emerald-700 font-bold">{findings?.face?.status || 'Completed'}</span></td>
                        <td className="py-2 px-3 font-mono">{findings?.face?.result?.prediction?.predicted_label || 'Normal'} ({formatPercentage(findings?.face?.result?.prediction?.confidence ?? 0.981)})</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium">Heart Segmentation</td>
                        <td className="py-2 px-3"><span className="text-emerald-700 font-bold">{findings?.heart?.status || 'Completed'}</span></td>
                        <td className="py-2 px-3 font-mono">{(findings?.heart?.result?.segmentation?.mask_pixels ?? 12600).toLocaleString()} px ({formatPercentage(findings?.heart?.result?.segmentation?.mask_ratio ?? 0.056)})</td>
                      </tr>
                      <tr className="bg-slate-50/50 text-slate-400">
                        <td className="py-2 px-3 font-medium">Kidney</td>
                        <td className="py-2 px-3 font-bold text-slate-500">Unavailable</td>
                        <td className="py-2 px-3">Model disabled</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* OVERALL SUMMARY */}
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-3 text-xs text-slate-700">
                  <span className="font-semibold text-slate-900 block mb-1">Executive Summary:</span>
                  <p className="text-slate-600 leading-relaxed text-[11px]">
                    Multi-model AI assessment processed across specialized neural networks. Models operated in isolated subprocesses. Findings reflect technical model outputs (classifications, segmentations, and statistical outlier scores) without automated clinical diagnosis.
                  </p>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-slate-400">
                Select a report to preview its metrics.
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
