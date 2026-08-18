import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  CalendarDays,
  CheckCircle2,
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
  getScans,
  getScan,
} from '../services/api';


// ============================================================
// HELPERS
// ============================================================

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }

        return (
          item?.msg ||
          String(item)
        );
      })
      .join(', ');
  }

  if (typeof detail === 'string') {
    return detail;
  }

  return (
    error?.response?.data?.message ||
    error?.message ||
    fallback
  );
}


function formatDate(value) {
  if (!value) {
    return '—';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return date.toLocaleString();
}


function formatPercentage(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return '—';
  }

  const percentage =
    number <= 1
      ? number * 100
      : number;

  return `${percentage.toFixed(2)}%`;
}


// ============================================================
// SCAN HISTORY PAGE
// ============================================================

function ScanHistoryPage() {
  const navigate = useNavigate();
  // ============================================================
  // STATE
  // ============================================================

  const [scans, setScans] = useState([]);

  const [selectedScan, setSelectedScan] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [loadingDetails, setLoadingDetails] =
    useState(false);

  const [error, setError] =
    useState('');

  const [search, setSearch] =
    useState('');

  const [filter, setFilter] =
    useState('all');


  // ============================================================
  // API BASE URL
  // ============================================================

  const apiBaseUrl = (
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    'http://127.0.0.1:8000'
  ).replace(/\/$/, '');


  // ============================================================
  // LOAD SCANS
  // ============================================================

  const loadScans = async () => {
    try {
      setLoading(true);
      setError('');

      const response =
        await getScans();

      const data =
        Array.isArray(response)
          ? response
          : response?.scans || [];

      setScans(data);

      if (data.length > 0) {
        setSelectedScan(data[0]);
      } else {
        setSelectedScan(null);
      }
    } catch (err) {
      console.error(
        'Scan history error:',
        err
      );

      setError(
        getErrorMessage(
          err,
          'Unable to load scan history.'
        )
      );
    } finally {
      setLoading(false);
    }
  };


  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    loadScans();
  }, []);


  // ============================================================
  // SELECT SCAN
  // ============================================================

  const handleSelectScan = async (
    scan
  ) => {
    try {
      setSelectedScan(scan);
      setLoadingDetails(true);
      setError('');

      const detail =
        await getScan(scan.id);

      if (detail) {
        setSelectedScan(detail);
      }
    } catch (err) {
      console.error(
        'Scan details error:',
        err
      );

      // Keep list data visible
      // even if detail request fails.

      setSelectedScan(scan);
    } finally {
      setLoadingDetails(false);
    }
  };


  // ============================================================
  // FILTERED SCANS
  // ============================================================

  const filteredScans = useMemo(() => {
    const query =
      search
        .trim()
        .toLowerCase();

    return scans.filter((scan) => {
      const matchesSearch =
        !query ||
        String(scan.id ?? '')
          .toLowerCase()
          .includes(query) ||
        String(scan.patient_id ?? '')
          .toLowerCase()
          .includes(query) ||
        String(scan.patient_name ?? '')
          .toLowerCase()
          .includes(query) ||
        String(scan.predicted_plane ?? '')
          .toLowerCase()
          .includes(query);

      if (!matchesSearch) {
        return false;
      }

      if (filter === 'brain') {
        return (
          scan.predicted_plane ===
          'Fetal brain'
        );
      }

      if (filter === 'other') {
        return (
          scan.predicted_plane !==
          'Fetal brain'
        );
      }

      return true;
    });
  }, [
    scans,
    search,
    filter,
  ]);


  // ============================================================
  // ANALYSIS
  // ============================================================

  const analysis =
    selectedScan?.analysis_result ||
    selectedScan?.analysis ||
    null;

  const brainPlane =
    analysis?.brain_plane ||
    null;

  const outlier =
    analysis?.outlier_analysis ||
    selectedScan?.outlier_analysis ||
    null;

  const explainability =
    selectedScan?.explainability ||
    analysis?.explainability ||
    analysis?.gradcam ||
    null;


  // ============================================================
  // EXPLAINABILITY
  // ============================================================

  const gradcamAvailable =
    explainability?.status ===
      'available' ||
    Boolean(
      explainability?.heatmap_path ||
      explainability?.overlay_path ||
      explainability?.heatmap_url ||
      explainability?.overlay_url
    );

  const gradcamHeatmapPath =
    explainability?.heatmap_url ||
    explainability?.heatmap_path ||
    '';

  const gradcamOverlayPath =
    explainability?.overlay_url ||
    explainability?.overlay_path ||
    '';


  // ============================================================
  // STORAGE URL
  // ============================================================

  const getStorageUrl = (path) => {
    if (!path) {
      return '';
    }

    let normalized =
      String(path)
        .trim()
        .replace(/\\/g, '/');

    if (
      normalized.startsWith(
        'http://'
      ) ||
      normalized.startsWith(
        'https://'
      )
    ) {
      return normalized;
    }

    normalized =
      normalized.replace(
        /^\/+/,
        ''
      );

    const storageIndex =
      normalized
        .toLowerCase()
        .indexOf('storage/');

    if (storageIndex >= 0) {
      normalized =
        normalized.substring(
          storageIndex
        );
    }

    if (
      !normalized
        .toLowerCase()
        .startsWith('storage/')
    ) {
      normalized =
        `storage/${normalized}`;
    }

    return `${apiBaseUrl}/${normalized}`;
  };


  const heatmapUrl =
    getStorageUrl(
      gradcamHeatmapPath
    );

  const overlayUrl =
    getStorageUrl(
      gradcamOverlayPath
    );


  // ============================================================
  // STATUS
  // ============================================================

  const getStatus = (scan) => {
    const scanAnalysis =
      scan?.analysis_result ||
      scan?.analysis ||
      null;

    const scanOutlier =
      scanAnalysis?.outlier_analysis ||
      scan?.outlier_analysis ||
      null;

    if (
      scanOutlier?.is_outlier === true
    ) {
      return {
        label: 'Review',
        className:
          'bg-amber-50 text-amber-700 border-amber-200',
      };
    }

    if (
      scanAnalysis &&
      scan?.predicted_plane ===
        'Fetal brain'
    ) {
      return {
        label: 'Brain Analysis',
        className:
          'bg-indigo-50 text-indigo-700 border-indigo-200',
      };
    }

    if (scanAnalysis) {
      return {
        label: 'Completed',
        className:
          'bg-emerald-50 text-emerald-700 border-emerald-200',
      };
    }

    return {
      label: 'Saved',
      className:
        'bg-slate-100 text-slate-600 border-slate-200',
    };
  };


  // ============================================================
  // LOADING
  // ============================================================

  if (loading) {
    return (
      <div className="space-y-6">

        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Scan History
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Review previous fetal ultrasound
            analyses and AI results.
          </p>
        </div>


        <Card>
          <div className="flex items-center gap-3 py-10 text-slate-500">

            <RefreshCw
              size={20}
              className="animate-spin"
            />

            Loading scan history...

          </div>
        </Card>

      </div>
    );
  }


  // ============================================================
  // MAIN
  // ============================================================

  return (
    <div className="space-y-6">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">

        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Scan History
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Review previous fetal ultrasound
            analyses and AI results.
          </p>
        </div>


        <Button
          type="button"
          variant="secondary"
          onClick={loadScans}
        >
          <RefreshCw
            size={17}
            className="mr-2"
          />

          Refresh
        </Button>

      </div>


      {/* ======================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">

          <div className="flex items-start gap-3 text-sm text-rose-700">

            <AlertTriangle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <span>
              {error}
            </span>

          </div>

        </div>
      )}


      {/* ======================================================
          FILTER BAR
      ====================================================== */}

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
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
              placeholder="Search scan, patient or plane..."
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pl-11 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
            />

          </div>


          <select
            value={filter}
            onChange={(event) =>
              setFilter(
                event.target.value
              )
            }
            className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
          >
            <option value="all">
              All scans
            </option>

            <option value="brain">
              Fetal brain
            </option>

            <option value="other">
              Other planes
            </option>
          </select>

        </div>

      </Card>


      {/* ======================================================
          EMPTY
      ====================================================== */}

      {!scans.length ? (
        <Card>

          <div className="flex min-h-[360px] flex-col items-center justify-center text-center">

            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">

              <ScanLine
                size={30}
              />

            </div>


            <h2 className="mt-5 text-lg font-semibold text-slate-800">
              No scans yet
            </h2>


            <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
              Completed ultrasound analyses
              will appear here automatically.
            </p>

          </div>

        </Card>
      ) : (

        <div className="grid gap-6 xl:grid-cols-[0.85fr_1.5fr]">

          {/* ==================================================
              SCAN LIST
          ================================================== */}

          <Card
            title="Previous Scans"
            subtitle={`${filteredScans.length} scan${
              filteredScans.length === 1
                ? ''
                : 's'
            }`}
          >

            <div className="mt-5 space-y-3">

              {!filteredScans.length ? (

                <div className="rounded-xl bg-slate-50 p-6 text-center">

                  <Search
                    size={22}
                    className="mx-auto text-slate-400"
                  />

                  <p className="mt-3 text-sm font-medium text-slate-700">
                    No matching scans
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    Try another search or filter.
                  </p>

                </div>

              ) : (

                filteredScans.map((scan) => {

                  const selected =
                    selectedScan?.id ===
                    scan.id;

                  const status =
                    getStatus(scan);

                  return (
                    <button
                      key={scan.id}
                      type="button"
                      onClick={() =>
                        handleSelectScan(
                          scan
                        )
                      }
                      className={`w-full rounded-2xl border p-4 text-left transition ${
                        selected
                          ? 'border-teal-500 bg-teal-50/70 shadow-sm'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >

                      <div className="flex items-start justify-between gap-3">

                        <div className="flex min-w-0 gap-3">

                          <div
                            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                              selected
                                ? 'bg-teal-100 text-teal-700'
                                : 'bg-slate-100 text-slate-500'
                            }`}
                          >
                            <FileImage
                              size={19}
                            />
                          </div>


                          <div className="min-w-0">

                            <p className="font-semibold text-slate-900">
                              Scan #{scan.id}
                            </p>


                            <p className="mt-1 truncate text-sm text-slate-500">
                              {scan.patient_id}
                              {' — '}
                              {scan.patient_name}
                            </p>

                          </div>

                        </div>


                        <span
                          className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-medium ${status.className}`}
                        >
                          {status.label}
                        </span>

                      </div>


                      <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">

                        <span className="truncate text-xs text-slate-500">
                          {scan.predicted_plane}
                        </span>


                        <span className="shrink-0 text-xs font-semibold text-slate-700">
                          {formatPercentage(
                            scan.confidence
                          )}
                        </span>

                      </div>


                      <div className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-400">

                        <CalendarDays
                          size={13}
                        />

                        {formatDate(
                          scan.created_at
                        )}

                      </div>

                    </button>
                  );
                })
              )}

            </div>

          </Card>


          {/* ==================================================
              DETAILS
          ================================================== */}

          <Card
            title={
              selectedScan
                ? `Scan #${selectedScan.id}`
                : 'Scan Details'
            }
            subtitle={
              selectedScan
                ? 'Complete AI analysis and explainability'
                : 'Select a scan to view details'
            }
          >

            {selectedScan ? (

              <div className="mt-5 space-y-5">

                {/* DETAIL LOADING */}

                {loadingDetails && (
                  <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">

                    <RefreshCw
                      size={16}
                      className="animate-spin"
                    />

                    Loading latest scan details...

                  </div>
                )}


                {/* PATIENT INFO */}

                <div className="rounded-2xl bg-slate-50 p-5">

                  <div className="flex items-center gap-3">

                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 text-teal-700">

                      <Activity
                        size={20}
                      />

                    </div>


                    <div>

                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        Patient
                      </p>

                      <p className="mt-1 font-semibold text-slate-900">
                        {selectedScan.patient_name}
                      </p>

                    </div>

                  </div>


                  <div className="mt-5 grid gap-4 sm:grid-cols-3">

                    <div>
                      <p className="text-xs text-slate-500">
                        Patient ID
                      </p>

                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {selectedScan.patient_id}
                      </p>
                    </div>


                    <div>
                      <p className="text-xs text-slate-500">
                        Scan date
                      </p>

                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {formatDate(
                          selectedScan.created_at
                        )}
                      </p>
                    </div>


                    <div>
                      <p className="text-xs text-slate-500">
                        Image
                      </p>

                      <p className="mt-1 truncate text-sm font-semibold text-slate-900">
                        {selectedScan.image_filename ||
                          '—'}
                      </p>
                    </div>

                  </div>

                </div>


                {/* FETAL + BRAIN */}

                <div className="grid gap-4 md:grid-cols-2">

                  {/* FETAL */}

                  <div className="rounded-2xl border border-slate-200 p-5">

                    <div className="flex items-center gap-3">

                      <div className="rounded-xl bg-teal-50 p-3 text-teal-600">

                        <Activity
                          size={21}
                        />

                      </div>


                      <div>

                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Fetal Plane
                        </p>

                        <p className="mt-1 text-lg font-semibold text-slate-900">
                          {selectedScan.predicted_plane ||
                            'Unknown'}
                        </p>

                      </div>

                    </div>


                    <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">

                      <span className="text-sm text-slate-500">
                        Confidence
                      </span>

                      <span className="font-semibold text-teal-700">
                        {formatPercentage(
                          selectedScan.confidence
                        )}
                      </span>

                    </div>

                  </div>


                  {/* BRAIN */}

                  <div className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-5">

                    <div className="flex items-center gap-3">

                      <div className="rounded-xl bg-indigo-100 p-3 text-indigo-700">

                        <Brain
                          size={21}
                        />

                      </div>


                      <div>

                        <p className="text-xs font-medium uppercase tracking-wide text-indigo-600">
                          Brain Plane
                        </p>

                        <p className="mt-1 text-lg font-semibold text-slate-900">
                          {brainPlane?.predicted_class ||
                            'Not available'}
                        </p>

                      </div>

                    </div>


                    <div className="mt-4 flex items-center justify-between border-t border-indigo-100 pt-4">

                      <span className="text-sm text-slate-500">
                        Confidence
                      </span>

                      <span className="font-semibold text-indigo-700">
                        {brainPlane
                          ? formatPercentage(
                              brainPlane.confidence_percent ??
                              brainPlane.confidence
                            )
                          : '—'}
                      </span>

                    </div>

                  </div>

                </div>


                {/* STATISTICAL SCREENING */}

                {outlier && (

                  <div
                    className={`rounded-2xl border p-5 ${
                      outlier.is_outlier
                        ? 'border-amber-200 bg-amber-50'
                        : 'border-emerald-200 bg-emerald-50'
                    }`}
                  >

                    <div className="flex items-center gap-3">

                      {outlier.is_outlier ? (
                        <AlertTriangle
                          size={21}
                          className="text-amber-600"
                        />
                      ) : (
                        <BarChart3
                          size={21}
                          className="text-emerald-600"
                        />
                      )}


                      <div>

                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Statistical Screening
                        </p>

                        <p className="mt-1 font-semibold text-slate-900">
                          {outlier.status ||
                            'Analysis completed'}
                        </p>

                      </div>

                    </div>


                    <div className="mt-4 grid gap-3 sm:grid-cols-3">

                      <div className="rounded-xl bg-white/70 p-3">

                        <p className="text-xs text-slate-500">
                          Anomaly score
                        </p>

                        <p className="mt-1 font-semibold text-slate-900">
                          {outlier.anomaly_score ??
                            '—'}
                        </p>

                      </div>


                      <div className="rounded-xl bg-white/70 p-3">

                        <p className="text-xs text-slate-500">
                          Threshold
                        </p>

                        <p className="mt-1 font-semibold text-slate-900">
                          {outlier.threshold ??
                            '—'}
                        </p>

                      </div>


                      <div className="rounded-xl bg-white/70 p-3">

                        <p className="text-xs text-slate-500">
                          Threshold ratio
                        </p>

                        <p className="mt-1 font-semibold text-slate-900">
                          {formatPercentage(
                            outlier.threshold_ratio
                          )}
                        </p>

                      </div>

                    </div>


                    {outlier.interpretation && (
                      <p className="mt-4 text-xs leading-5 text-slate-600">
                        {outlier.interpretation}
                      </p>
                    )}

                  </div>

                )}


                {/* GRAD-CAM */}

                <div className="overflow-hidden rounded-2xl border border-violet-200 bg-white">

                  <div className="border-b border-violet-100 bg-violet-50/60 p-5">

                    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">

                      <div className="flex items-center gap-3">

                        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-100 text-violet-700">

                          <Eye
                            size={21}
                          />

                        </div>


                        <div>

                          <p className="text-xs font-semibold uppercase tracking-wide text-violet-600">
                            AI Explainability
                          </p>

                          <h3 className="mt-1 text-lg font-semibold text-slate-900">
                            Grad-CAM Analysis
                          </h3>

                          <p className="mt-1 text-xs leading-5 text-slate-500">
                            Visual explanation of where the
                            fetal-plane model focused.
                          </p>

                        </div>

                      </div>


                      <span
                        className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                          gradcamAvailable
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {gradcamAvailable
                          ? 'Available'
                          : 'Unavailable'}
                      </span>

                    </div>

                  </div>


                  {gradcamAvailable ? (

                    <div className="p-5">

                      {/* METRICS */}

                      <div className="grid gap-3 sm:grid-cols-3">

                        <div className="rounded-xl bg-slate-50 p-4">

                          <p className="text-xs text-slate-500">
                            Target class
                          </p>

                          <p className="mt-1 font-semibold text-slate-900">
                            {explainability.target_class ||
                              selectedScan.predicted_plane ||
                              '—'}
                          </p>

                        </div>


                        <div className="rounded-xl bg-slate-50 p-4">

                          <p className="text-xs text-slate-500">
                            Confidence
                          </p>

                          <p className="mt-1 font-semibold text-violet-700">
                            {formatPercentage(
                              explainability.confidence_percent ??
                              explainability.confidence
                            )}
                          </p>

                        </div>


                        <div className="rounded-xl bg-slate-50 p-4">

                          <p className="text-xs text-slate-500">
                            Status
                          </p>

                          <p className="mt-1 font-semibold text-emerald-700">
                            {explainability.status ||
                              'Available'}
                          </p>

                        </div>

                      </div>


                      {/* IMAGES */}

                      <div className="mt-5 grid gap-5 lg:grid-cols-2">

                        {/* HEATMAP */}

                        <div className="overflow-hidden rounded-2xl border border-slate-200">

                          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">

                            <div className="flex items-center gap-2">

                              <ScanLine
                                size={16}
                                className="text-violet-600"
                              />

                              <p className="text-sm font-semibold text-slate-800">
                                Grad-CAM Heatmap
                              </p>

                            </div>

                            <span className="text-[11px] text-slate-400">
                              Attention map
                            </span>

                          </div>


                          <div className="flex min-h-[280px] items-center justify-center bg-slate-950">

                            {heatmapUrl ? (

                              <img
                                src={heatmapUrl}
                                alt="Grad-CAM heatmap"
                                className="max-h-[360px] w-full object-contain"
                                loading="lazy"
                              />

                            ) : (

                              <div className="px-5 text-center text-sm text-slate-400">
                                Heatmap path is unavailable.
                              </div>

                            )}

                          </div>

                        </div>


                        {/* OVERLAY */}

                        <div className="overflow-hidden rounded-2xl border border-slate-200">

                          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">

                            <div className="flex items-center gap-2">

                              <FileImage
                                size={16}
                                className="text-violet-600"
                              />

                              <p className="text-sm font-semibold text-slate-800">
                                Heatmap Overlay
                              </p>

                            </div>

                            <span className="text-[11px] text-slate-400">
                              Ultrasound + attention
                            </span>

                          </div>


                          <div className="flex min-h-[280px] items-center justify-center bg-slate-950">

                            {overlayUrl ? (

                              <img
                                src={overlayUrl}
                                alt="Grad-CAM overlay"
                                className="max-h-[360px] w-full object-contain"
                                loading="lazy"
                              />

                            ) : (

                              <div className="px-5 text-center text-sm text-slate-400">
                                Overlay path is unavailable.
                              </div>

                            )}

                          </div>

                        </div>

                      </div>


                      {/* DISCLAIMER */}

                      <div className="mt-5 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">

                        <AlertTriangle
                          size={16}
                          className="mt-0.5 shrink-0 text-amber-700"
                        />

                        <p className="text-xs leading-5 text-amber-800">
                          Grad-CAM is an explainability
                          visualization. Highlighted regions
                          represent model attention and are
                          not a clinical diagnosis or anatomical
                          segmentation.
                        </p>

                      </div>

                    </div>

                  ) : (

                    <div className="p-5">

                      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">

                        <Info
                          size={18}
                          className="mt-0.5 shrink-0 text-slate-400"
                        />

                        <div>

                          <p className="text-sm font-semibold text-slate-700">
                            Explainability unavailable
                          </p>

                          <p className="mt-1 text-xs leading-5 text-slate-500">
                            Grad-CAM output was not available
                            for this scan. The underlying AI
                            classification remains available.
                          </p>

                        </div>

                      </div>

                    </div>

                  )}

                </div>


                {/* PIPELINE SUMMARY */}

                <div className="rounded-2xl border border-slate-200 p-5">

                  <div className="flex items-center gap-3">

                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">

                      <ShieldCheck
                        size={20}
                      />

                    </div>


                    <div>

                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Pipeline Summary
                      </p>

                      <p className="mt-1 font-semibold text-slate-900">
                        AI analysis stages
                      </p>

                    </div>

                  </div>


                  <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">

                    <div className="rounded-xl bg-slate-50 p-4">

                      <p className="text-xs text-slate-500">
                        Fetal Plane Classification
                      </p>

                      <p className="mt-1 font-semibold text-emerald-600">
                        Completed
                      </p>

                    </div>


                    <div className="rounded-xl bg-slate-50 p-4">

                      <p className="text-xs text-slate-500">
                        Brain Plane Classification
                      </p>

                      <p className="mt-1 font-semibold text-emerald-600">
                        {brainPlane
                          ? 'Completed'
                          : 'Not applicable'}
                      </p>

                    </div>


                    <div className="rounded-xl bg-slate-50 p-4">

                      <p className="text-xs text-slate-500">
                        Statistical Outlier Analysis
                      </p>

                      <p className="mt-1 font-semibold text-emerald-600">
                        {outlier
                          ? 'Completed'
                          : 'Not applicable'}
                      </p>

                    </div>


                    <div className="rounded-xl bg-slate-50 p-4">

                      <p className="text-xs text-slate-500">
                        Grad-CAM Explainability
                      </p>

                      <p
                        className={`mt-1 font-semibold ${
                          gradcamAvailable
                            ? 'text-violet-600'
                            : 'text-slate-400'
                        }`}
                      >
                        {gradcamAvailable
                          ? 'Generated'
                          : 'Unavailable'}
                      </p>

                    </div>

                  </div>

                </div>


                {/* REPORT CONNECTION */}

                <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-5">

                  <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">

                    <div className="flex items-start gap-3">

                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 text-teal-700">

                        <FileText
                          size={19}
                        />

                      </div>


                      <div>

                        <p className="font-semibold text-slate-900">
                          Full AI Report
                        </p>

                        <p className="mt-1 text-xs leading-5 text-slate-500">
                          Open the complete report for
                          this scan, including detailed
                          analysis and PDF export.
                        </p>

                      </div>

                    </div>


                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => {
                        navigate(
                          `/reports?scan=${encodeURIComponent(
                            selectedScan.id
                          )}`
                        );
                      }}
                    >

                      <FileText
                        size={16}
                        className="mr-2"
                      />

                      Open Full Report

                    </Button>

                  </div>

                </div>


                {/* CLINICAL DISCLAIMER */}

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">

                  <div className="flex items-start gap-3">

                    <AlertTriangle
                      size={18}
                      className="mt-0.5 shrink-0 text-amber-600"
                    />

                    <div>

                      <p className="text-sm font-semibold text-amber-900">
                        Clinical note
                      </p>

                      <p className="mt-1 text-xs leading-5 text-amber-800">
                        FetalAI provides experimental
                        AI-assisted analysis and statistical
                        screening. Results are not a clinically
                        validated diagnosis and should not
                        replace evaluation by a qualified
                        medical professional.
                      </p>

                    </div>

                  </div>

                </div>

              </div>

            ) : (

              <div className="flex min-h-[400px] flex-col items-center justify-center text-center">

                <Eye
                  size={30}
                  className="text-slate-300"
                />

                <p className="mt-4 text-sm font-semibold text-slate-700">
                  Select a scan
                </p>

                <p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">
                  Select a scan from the history list
                  to view its complete AI analysis.
                </p>

              </div>

            )}

          </Card>

        </div>
      )}

    </div>
  );
}


export default ScanHistoryPage;