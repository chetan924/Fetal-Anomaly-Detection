import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

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
} from 'lucide-react';

import jsPDF from 'jspdf';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

import { getScans, getScan } from '../services/api';


// ============================================================
// REPORTS PAGE
// ============================================================

function ReportsPage() {

  // ==========================================================
  // URL SEARCH PARAMS
  // ==========================================================

  const [
    searchParams,
    setSearchParams,
  ] = useSearchParams();

  const requestedScanId =
    searchParams.get('scan');


  // ==========================================================
  // STATE
  // ==========================================================

  const [scans, setScans] = useState([]);

  const [selectedScan, setSelectedScan] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');

  const [generatingPdf, setGeneratingPdf] =
    useState(false);

  const [heatmapError, setHeatmapError] =
    useState(false);

  const [overlayError, setOverlayError] =
    useState(false);


  // ==========================================================
  // LOAD REPORTS
  // ==========================================================

  const loadReports = async () => {

    try {

      setLoading(true);
      setError('');

      // Load all scans for the report selector.
      const scanData =
        await getScans();

      const scanList =
        Array.isArray(scanData)
          ? scanData
          : [];

      setScans(scanList);

      // ======================================================
      // EXACT SCAN FROM URL
      // /reports?scan=31
      // ======================================================

      if (requestedScanId) {

        const numericScanId =
          Number(requestedScanId);

        if (
          !Number.isInteger(
            numericScanId
          ) ||
          numericScanId <= 0
        ) {

          setSelectedScan(null);

          setError(
            `Invalid scan ID: ${requestedScanId}`
          );

          return;
        }

        try {

          // Fetch the exact scan directly
          // from GET /api/scans/{scan_id}

          const requestedScan =
            await getScan(
              numericScanId
            );

          if (!requestedScan) {

            throw new Error(
              `Scan #${requestedScanId} was not found.`
            );

          }

          setSelectedScan(
            requestedScan
          );

          setError('');

        } catch (scanError) {

          console.error(
            'Requested scan loading error:',
            scanError
          );

          setSelectedScan(null);

          setError(
            scanError?.response?.data?.detail ||
            scanError?.message ||
            `Scan #${requestedScanId} was not found.`
          );

        }

        return;
      }

      // ======================================================
      // NORMAL /reports PAGE
      // No ?scan=ID → latest scan
      // ======================================================

      if (scanList.length > 0) {

        setSelectedScan(
          scanList[0]
        );

      } else {

        setSelectedScan(null);

      }

    } catch (err) {

      console.error(
        'Reports loading error:',
        err
      );

      setError(
        err?.response?.data?.detail ||
        err?.message ||
        'Unable to load scan reports.'
      );

      setSelectedScan(null);

    } finally {

      setLoading(false);

    }
  };


  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {

    loadReports();

  }, [requestedScanId]);


  // ==========================================================
  // RESET GRAD-CAM ERRORS
  // ==========================================================

  useEffect(() => {

    setHeatmapError(false);
    setOverlayError(false);

  }, [selectedScan]);


  // ==========================================================
  // HELPERS
  // ==========================================================

  const safeText = (value) => {

    if (
      value === null ||
      value === undefined ||
      value === ''
    ) {

      return '—';

    }

    return String(value);

  };


  const formatDate = (value) => {

    if (!value) {
      return '—';
    }

    const date =
      new Date(value);

    if (
      Number.isNaN(
        date.getTime()
      )
    ) {

      return '—';

    }

    return date.toLocaleString();

  };


  // ==========================================================
  // PERCENTAGE HELPER
  // ==========================================================
  //
  // Handles both:
  //
  // 0.9999  -> 99.99%
  // 99.99   -> 99.99%
  //
  // ==========================================================

  const formatPercentage = (
    value,
    fallback = '—'
  ) => {

    const number =
      Number(value);

    if (
      !Number.isFinite(number)
    ) {

      return fallback;

    }

    const percentage =
      number <= 1
        ? number * 100
        : number;

    return `${percentage.toFixed(2)}%`;

  };


  const percentageNumber = (
    value
  ) => {

    const number =
      Number(value);

    if (
      !Number.isFinite(number)
    ) {

      return 0;

    }

    return number <= 1
      ? number * 100
      : number;

  };


  // ==========================================================
  // API BASE URL
  // ==========================================================

  const apiBaseUrl = (
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    (import.meta.env.PROD
      ? 'https://fetalai-backend.onrender.com'
      : 'http://127.0.0.1:8000')
  ).replace(/\/+$/, '');



  // ==========================================================
  // STORAGE URL HELPER
  // ==========================================================
  //
  // Supports:
  //
  // /storage/explainability/file.png
  // storage/explainability/file.png
  // D:\...\storage\explainability\file.png
  // http://...
  //
  // ==========================================================

  const getStorageUrl = (
    path
  ) => {

    if (!path) {
      return '';
    }


    let normalizedPath =
      String(path)
        .trim()
        .replace(
          /\\/g,
          '/'
        );


    if (!normalizedPath) {
      return '';
    }


    // --------------------------------------------------------
    // Absolute URL
    // --------------------------------------------------------

    if (
      normalizedPath.startsWith(
        'http://'
      ) ||
      normalizedPath.startsWith(
        'https://'
      )
    ) {

      return normalizedPath;

    }


    // --------------------------------------------------------
    // Remove leading slash
    // --------------------------------------------------------

    normalizedPath =
      normalizedPath.replace(
        /^\/+/,
        ''
      );


    // --------------------------------------------------------
    // Extract storage path from Windows filesystem path
    // --------------------------------------------------------

    const storageIndex =
      normalizedPath
        .toLowerCase()
        .indexOf(
          'storage/'
        );


    if (
      storageIndex >= 0
    ) {

      normalizedPath =
        normalizedPath.substring(
          storageIndex
        );

    }


    // --------------------------------------------------------
    // Ensure storage prefix
    // --------------------------------------------------------

    if (
      !normalizedPath
        .toLowerCase()
        .startsWith(
          'storage/'
        )
    ) {

      normalizedPath =
        `storage/${normalizedPath}`;

    }


    // --------------------------------------------------------
    // Remove /api from API URL if present
    // --------------------------------------------------------

    const backendBaseUrl =
      String(apiBaseUrl)
        .replace(
          /\/+$/,
          ''
        )
        .replace(
          /\/api$/i,
          ''
        );


    return (
      `${backendBaseUrl}/${normalizedPath}`
    );

  };


  // ==========================================================
  // ANALYSIS DATA
  // ==========================================================

  const analysis =
    selectedScan?.analysis_result ||
    selectedScan?.analysis ||
    {};


  const fetalPlane =
    analysis?.fetal_plane ||
    {};


  const brainPlane =
    analysis?.brain_plane ||
    {};


  const outlier =
    analysis?.outlier_analysis ||
    {};


  const explainability =
    analysis?.explainability ||
    analysis?.gradcam ||
    selectedScan?.explainability ||
    selectedScan?.gradcam ||
    null;


  // ==========================================================
  // FETAL PLANE
  // ==========================================================

  const fetalPrediction =
    fetalPlane?.predicted_class ||
    selectedScan?.predicted_plane ||
    'Unknown';


  const fetalConfidence =
    percentageNumber(
      fetalPlane?.confidence ??
      fetalPlane?.confidence_percent ??
      selectedScan?.confidence ??
      0
    );


  // ==========================================================
  // BRAIN PLANE
  // ==========================================================

  const brainPrediction =
    brainPlane?.predicted_class ||
    'Not available';


  const brainConfidence =
    percentageNumber(
      brainPlane?.confidence_percent ??
      brainPlane?.confidence ??
      0
    );


  const requiredBrainConfidence =
    Number(
      analysis?.required_confidence ??
      70
    );


  const brainAnalysisPerformed =
    analysis?.brain_analysis_performed === true;


  const brainPlaneAvailable =
    Boolean(
      analysis?.brain_plane
    );


  // ==========================================================
  // STATISTICAL SCREENING
  // ==========================================================

  const anomalyScore =
    Number(
      outlier?.anomaly_score
    );


  const threshold =
    Number(
      outlier?.threshold
    );


  const rawThresholdRatio =
    Number(
      outlier?.threshold_ratio
    );


  const hasStatisticalMetrics =
    Number.isFinite(
      anomalyScore
    ) &&
    Number.isFinite(
      threshold
    ) &&
    threshold > 0;


  const calculatedRatio =
    hasStatisticalMetrics
      ? (
          anomalyScore /
          threshold
        )
      : NaN;


  const thresholdRatio =
    Number.isFinite(
      rawThresholdRatio
    )
      ? rawThresholdRatio
      : calculatedRatio;


  const thresholdRatioPercent =
    Number.isFinite(
      thresholdRatio
    )
      ? (
          thresholdRatio <= 1
            ? thresholdRatio * 100
            : thresholdRatio
        )
      : 0;


  const isStatisticalOutlier =
    outlier?.is_outlier === true ||
    String(
      outlier?.status || ''
    )
      .toLowerCase()
      .includes(
        'outlier'
      ) ||
    String(
      outlier?.status || ''
    )
      .toLowerCase()
      .includes(
        'flag'
      );


  const statisticalStatus =
    isStatisticalOutlier
      ? 'Potential outlier'
      : (
          outlier?.status ||
          'In-distribution'
        );


  // ==========================================================
  // GRAD-CAM
  // ==========================================================

  const gradcamHeatmapPath =
    explainability?.heatmap_url ||
    explainability?.heatmap_path ||
    explainability?.heatmap ||
    '';


  const gradcamOverlayPath =
    explainability?.overlay_url ||
    explainability?.overlay_path ||
    explainability?.overlay ||
    '';


  const gradcamHeatmapUrl =
    getStorageUrl(
      gradcamHeatmapPath
    );


  const gradcamOverlayUrl =
    getStorageUrl(
      gradcamOverlayPath
    );


  const gradcamAvailable =
    Boolean(
      explainability &&
      (
        gradcamHeatmapUrl ||
        gradcamOverlayUrl
      )
    );


  const attentionScore =
    Number(
      explainability
        ?.attention_concentration
        ?.score ??
      explainability?.attention_score
    );


  const attentionStatus =
    explainability
      ?.attention_concentration
      ?.status ||
    explainability?.attention_status ||
    '—';


  const attentionInterpretation =
    explainability
      ?.attention_concentration
      ?.interpretation ||
    explainability?.interpretation ||
    '—';


  const attentionEntropy =
    Number(
      explainability
        ?.attention_concentration
        ?.entropy ??
      explainability?.entropy
    );


  // ==========================================================
  // PIPELINE STATUS
  // ==========================================================

  const pipelineStatus =
    analysis?.pipeline_status ||
    analysis?.status ||
    'Analysis completed';


  const pipelineMessage =
    analysis?.message ||
    'AI processing completed for this scan.';


  // ==========================================================
  // PDF GENERATION
  // ==========================================================

  const generatePdf = () => {

    if (!selectedScan) {
      return;
    }


    try {

      setGeneratingPdf(true);


      const doc =
        new jsPDF({
          orientation: 'portrait',
          unit: 'mm',
          format: 'a4',
        });


      const pageWidth =
        doc.internal.pageSize.getWidth();


      const pageHeight =
        doc.internal.pageSize.getHeight();


      const margin = 18;

      let y = 20;


      // ------------------------------------------------------
      // PAGE HELPERS
      // ------------------------------------------------------

      const ensureSpace = (
        requiredHeight = 15
      ) => {

        if (
          y + requiredHeight >
          pageHeight - 18
        ) {

          doc.addPage();

          y = 20;

        }

      };


      const addSectionTitle = (
        title
      ) => {

        ensureSpace(16);

        doc.setFont(
          'helvetica',
          'bold'
        );

        doc.setFontSize(13);

        doc.setTextColor(
          15,
          23,
          42
        );

        doc.text(
          title,
          margin,
          y
        );

        y += 7;

      };


      const addLabelValue = (
        label,
        value
      ) => {

        ensureSpace(9);

        doc.setFont(
          'helvetica',
          'bold'
        );

        doc.setFontSize(9);

        doc.setTextColor(
          71,
          85,
          105
        );

        doc.text(
          `${label}:`,
          margin,
          y
        );

        doc.setFont(
          'helvetica',
          'normal'
        );

        doc.setTextColor(
          15,
          23,
          42
        );

        doc.text(
          safeText(value),
          margin + 35,
          y
        );

        y += 6;

      };


      const addParagraph = (
        text
      ) => {

        ensureSpace(18);

        doc.setFont(
          'helvetica',
          'normal'
        );

        doc.setFontSize(9);

        doc.setTextColor(
          71,
          85,
          105
        );

        const lines =
          doc.splitTextToSize(
            safeText(text),
            pageWidth - (
              margin * 2
            )
          );

        doc.text(
          lines,
          margin,
          y
        );

        y += (
          lines.length * 4.5
        ) + 4;

      };


      // ------------------------------------------------------
      // HEADER
      // ------------------------------------------------------

      doc.setFont(
        'helvetica',
        'bold'
      );

      doc.setFontSize(22);

      doc.setTextColor(
        15,
        23,
        42
      );

      doc.text(
        'FetalAI',
        margin,
        y
      );

      y += 8;


      doc.setFont(
        'helvetica',
        'normal'
      );

      doc.setFontSize(14);

      doc.text(
        'AI Analysis Report',
        margin,
        y
      );

      y += 7;


      doc.setFontSize(9);

      doc.setTextColor(
        100,
        116,
        139
      );

      doc.text(
        'AI-assisted fetal ultrasound analysis',
        margin,
        y
      );

      y += 8;


      doc.setDrawColor(
        203,
        213,
        225
      );

      doc.line(
        margin,
        y,
        pageWidth - margin,
        y
      );

      y += 10;


      // ------------------------------------------------------
      // REPORT META
      // ------------------------------------------------------

      addSectionTitle(
        'Patient / Scan Information'
      );


      addLabelValue(
        'Scan ID',
        `#${safeText(
          selectedScan.id
        )}`
      );


      addLabelValue(
        'Patient ID',
        selectedScan.patient_id
      );


      addLabelValue(
        'Patient Name',
        selectedScan.patient_name
      );


      addLabelValue(
        'Image',
        selectedScan.image_filename
      );


      addLabelValue(
        'Created',
        formatDate(
          selectedScan.created_at
        )
      );


      // ------------------------------------------------------
      // FETAL PLANE
      // ------------------------------------------------------

      addSectionTitle(
        '1. Fetal Plane Classification'
      );


      addLabelValue(
        'Prediction',
        fetalPrediction
      );


      addLabelValue(
        'Confidence',
        `${fetalConfidence.toFixed(2)}%`
      );


      y += 3;


      // ------------------------------------------------------
      // BRAIN PLANE
      // ------------------------------------------------------

      addSectionTitle(
        '2. Brain Plane Classification'
      );


      addLabelValue(
        'Prediction',
        brainPlaneAvailable
          ? brainPrediction
          : 'Not available'
      );


      addLabelValue(
        'Confidence',
        brainPlaneAvailable
          ? `${brainConfidence.toFixed(2)}%`
          : '—'
      );


      addLabelValue(
        'Status',
        brainAnalysisPerformed
          ? 'Completed'
          : 'Not applicable'
      );


      // ------------------------------------------------------
      // STATISTICAL
      // ------------------------------------------------------

      addSectionTitle(
        '3. Statistical Screening'
      );


      addLabelValue(
        'Status',
        statisticalStatus
      );


      addLabelValue(
        'Anomaly Score',
        hasStatisticalMetrics
          ? anomalyScore.toFixed(4)
          : '—'
      );


      addLabelValue(
        'Threshold',
        hasStatisticalMetrics
          ? threshold.toFixed(4)
          : '—'
      );


      addLabelValue(
        'Threshold Ratio',
        Number.isFinite(
          thresholdRatioPercent
        )
          ? `${thresholdRatioPercent.toFixed(2)}%`
          : '—'
      );


      if (outlier?.interpretation) {

        addParagraph(
          outlier.interpretation
        );

      }


      // ------------------------------------------------------
      // EXPLAINABILITY
      // ------------------------------------------------------

      addSectionTitle(
        '4. AI Explainability'
      );


      addLabelValue(
        'Target Class',
        explainability?.target_class ||
        fetalPrediction
      );


      addLabelValue(
        'Attention Score',
        Number.isFinite(
          attentionScore
        )
          ? attentionScore.toFixed(4)
          : '—'
      );


      addLabelValue(
        'Attention Status',
        attentionStatus
      );


      if (
        attentionInterpretation !== '—'
      ) {

        addParagraph(
          attentionInterpretation
        );

      }


      // ------------------------------------------------------
      // PIPELINE
      // ------------------------------------------------------

      addSectionTitle(
        'Pipeline Summary'
      );


      addLabelValue(
        'Fetal Plane',
        `${fetalPrediction} — ${fetalConfidence.toFixed(2)}%`
      );


      addLabelValue(
        'Brain Plane',
        brainAnalysisPerformed
          ? `${brainPrediction} — ${brainConfidence.toFixed(2)}%`
          : 'Not applicable'
      );


      addLabelValue(
        'Statistical Screening',
        statisticalStatus
      );


      addLabelValue(
        'Explainability',
        gradcamAvailable
          ? 'Grad-CAM generated'
          : 'Not available'
      );


      addLabelValue(
        'Pipeline Status',
        pipelineStatus
      );


      // ------------------------------------------------------
      // CLINICAL DISCLAIMER
      // ------------------------------------------------------

      ensureSpace(35);

      doc.setFillColor(
        255,
        247,
        237
      );

      doc.setDrawColor(
        253,
        186,
        116
      );

      doc.roundedRect(
        margin,
        y,
        pageWidth - (
          margin * 2
        ),
        30,
        3,
        3,
        'FD'
      );


      y += 7;


      doc.setFont(
        'helvetica',
        'bold'
      );

      doc.setFontSize(9);

      doc.setTextColor(
        124,
        45,
        18
      );

      doc.text(
        'Clinical / Experimental Disclaimer',
        margin + 5,
        y
      );

      y += 5;


      doc.setFont(
        'helvetica',
        'normal'
      );

      doc.setFontSize(8);

      const disclaimer =
        'FetalAI provides experimental AI-assisted analysis and statistical screening results. These outputs are not a clinically validated diagnosis and should not replace evaluation by a qualified medical professional. Grad-CAM attention metrics are explainability metrics only.';


      const disclaimerLines =
        doc.splitTextToSize(
          disclaimer,
          pageWidth - (
            margin * 2
          ) - 10
        );


      doc.text(
        disclaimerLines,
        margin + 5,
        y
      );


      y += (
        disclaimerLines.length *
        4
      ) + 8;


      // ------------------------------------------------------
      // FOOTER
      // ------------------------------------------------------

      ensureSpace(10);

      doc.setFontSize(7);

      doc.setTextColor(
        100,
        116,
        139
      );

      doc.text(
        'FetalAI v2.4 • For research and screening use only',
        margin,
        pageHeight - 10
      );


      // ------------------------------------------------------
      // SAVE
      // ------------------------------------------------------

      doc.save(
        `FetalAI_Report_Scan_${selectedScan.id}.pdf`
      );


    } catch (err) {

      console.error(
        'PDF generation error:',
        err
      );

      setError(
        'Unable to generate the PDF report.'
      );

    } finally {

      setGeneratingPdf(false);

    }

  };


  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {

    return (

      <div className="space-y-6">

        <div>

          <h1 className="text-2xl font-semibold text-slate-900">
            Reports
          </h1>

          <p className="mt-2 text-slate-500">
            Review AI analysis reports generated
            from ultrasound scans.
          </p>

        </div>


        <Card>

          <div className="flex items-center gap-3 text-slate-500">

            <RefreshCw
              size={20}
              className="animate-spin"
            />

            Loading reports...

          </div>

        </Card>

      </div>

    );

  }


  // ==========================================================
  // ERROR
  // ==========================================================

  if (
    error &&
    scans.length === 0
  ) {

    return (

      <div className="space-y-6">

        <div>

          <h1 className="text-2xl font-semibold text-slate-900">
            Reports
          </h1>

          <p className="mt-2 text-slate-500">
            Review AI analysis reports generated
            from ultrasound scans.
          </p>

        </div>


        <Card>

          <div className="rounded-xl border border-rose-200 bg-rose-50 p-5">

            <div className="flex items-center gap-3 text-rose-700">

              <AlertTriangle
                size={20}
              />

              <span>
                {error}
              </span>

            </div>


            <Button
              type="button"
              variant="secondary"
              className="mt-4"
              onClick={loadReports}
            >

              Try again

            </Button>

          </div>

        </Card>

      </div>

    );

  }


  // ==========================================================
  // EMPTY
  // ==========================================================

  if (!scans.length) {

    return (

      <div className="space-y-6">

        <div>

          <h1 className="text-2xl font-semibold text-slate-900">
            Reports
          </h1>

          <p className="mt-2 text-slate-500">
            Review AI analysis reports generated
            from ultrasound scans.
          </p>

        </div>


        <Card>

          <div className="flex min-h-[300px] flex-col items-center justify-center text-center">

            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">

              <FileText
                size={26}
              />

            </div>


            <p className="mt-4 font-semibold text-slate-800">
              No reports available
            </p>


            <p className="mt-1 max-w-sm text-sm text-slate-500">

              Upload and analyze an ultrasound
              scan first to generate an AI report.

            </p>


            <Button
              type="button"
              variant="secondary"
              className="mt-5"
              onClick={loadReports}
            >

              <RefreshCw
                size={17}
                className="mr-2"
              />

              Refresh

            </Button>

          </div>

        </Card>

      </div>

    );

  }


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

          <div className="flex items-center gap-3">

            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-50 text-teal-700">

              <FileText
                size={22}
              />

            </div>


            <div>

              <h1 className="text-2xl font-semibold text-slate-900">
                Reports
              </h1>

              <p className="mt-1 text-sm text-slate-500">

                Review complete AI analysis reports
                generated from ultrasound scans.

              </p>

            </div>

          </div>

        </div>


        <div className="flex flex-wrap gap-2">

          <Button
            type="button"
            variant="secondary"
            onClick={loadReports}
          >

            <RefreshCw
              size={17}
              className="mr-2"
            />

            Refresh

          </Button>


          <Button
            type="button"
            onClick={generatePdf}
            disabled={
              generatingPdf ||
              !selectedScan
            }
          >

            {generatingPdf ? (

              <RefreshCw
                size={17}
                className="mr-2 animate-spin"
              />

            ) : (

              <Download
                size={17}
                className="mr-2"
              />

            )}


            {generatingPdf
              ? 'Generating...'
              : 'Download PDF'}

          </Button>

        </div>

      </div>


      {/* ====================================================
          LOAD ERROR WITH DATA
      ==================================================== */}

      {error &&
        scans.length > 0 && (

          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">

            <div className="flex items-center gap-3 text-sm text-rose-700">

              <AlertTriangle
                size={18}
              />

              <span>
                {error}
              </span>

            </div>

          </div>

        )}


      {/* ====================================================
          REPORT SELECTOR
      ==================================================== */}

      <Card
        title="Available Reports"
        subtitle={`${scans.length} scan${
          scans.length === 1
            ? ''
            : 's'
        } available`}
      >

        <div className="grid gap-3">

          {scans.map(
            (scan) => {

              const isSelected =
                selectedScan?.id ===
                scan.id;


              const confidence =
                percentageNumber(
                  scan.confidence
                );


              return (

                <button
                  key={scan.id}
                  type="button"

                  // ==================================================
                  // STEP 9:
                  // Keep selected scan synchronized with URL.
                  // ==================================================

                  onClick={() => {

                    setSelectedScan(
                      scan
                    );

                    setSearchParams(
                      {
                        scan: String(
                          scan.id
                        ),
                      },
                      {
                        replace: true,
                      }
                    );

                  }}

                  className={`flex w-full items-center justify-between gap-4 rounded-xl border p-4 text-left transition ${
                    isSelected
                      ? 'border-teal-500 bg-teal-50'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >

                  <div className="min-w-0">

                    <div className="flex items-center gap-2">

                      <FileText
                        size={17}
                        className={
                          isSelected
                            ? 'text-teal-700'
                            : 'text-slate-400'
                        }
                      />


                      <p className="font-semibold text-slate-900">

                        Scan #{scan.id}

                      </p>

                    </div>


                    <p className="mt-1 text-sm text-slate-500">

                      {safeText(
                        scan.patient_id
                      )}

                      {' — '}

                      {safeText(
                        scan.patient_name
                      )}

                    </p>


                    <p className="mt-1 text-xs text-slate-400">

                      {formatDate(
                        scan.created_at
                      )}

                    </p>

                  </div>


                  <div className="shrink-0 text-right">

                    <p className="text-sm font-semibold text-slate-800">

                      {safeText(
                        scan.predicted_plane
                      )}

                    </p>


                    <p className="mt-1 text-xs text-slate-500">

                      {confidence.toFixed(2)}%

                    </p>

                  </div>

                </button>

              );

            }
          )}

        </div>

      </Card>


      {/* ====================================================
          REPORT
      ==================================================== */}

      {selectedScan && (

        <Card
          title={`AI Analysis Report — Scan #${selectedScan.id}`}
          subtitle="Generated from the FetalAI analysis pipeline."
        >

          <div className="space-y-6">

            {/* =================================================
                REPORT HEADER
            ================================================= */}

            <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-5">

              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">

                <div className="flex items-center gap-3">

                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-100 text-teal-700">

                    <CheckCircle2
                      size={22}
                    />

                  </div>


                  <div>

                    <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
                      AI Analysis Complete
                    </p>


                    <p className="mt-1 font-semibold text-slate-900">
                      Complete analysis for Scan #{selectedScan.id}
                    </p>

                  </div>

                </div>


                <div className="rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-700">

                  {pipelineStatus}

                </div>

              </div>


              <p className="mt-4 text-sm leading-6 text-slate-600">

                {pipelineMessage}

              </p>

            </div>


            {/* =================================================
                PATIENT INFORMATION
            ================================================= */}

            <div className="rounded-2xl bg-slate-50 p-5">

              <div className="flex items-center gap-3">

                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-slate-600 shadow-sm">

                  <FileText
                    size={19}
                  />

                </div>


                <div>

                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                    Patient / Scan Information
                  </h3>

                </div>

              </div>


              <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">

                <div>

                  <p className="text-xs text-slate-500">
                    Patient ID
                  </p>

                  <p className="mt-1 font-semibold text-slate-900">
                    {safeText(
                      selectedScan.patient_id
                    )}
                  </p>

                </div>


                <div>

                  <p className="text-xs text-slate-500">
                    Patient Name
                  </p>

                  <p className="mt-1 font-semibold text-slate-900">
                    {safeText(
                      selectedScan.patient_name
                    )}
                  </p>

                </div>


                <div>

                  <p className="text-xs text-slate-500">
                    Scan ID
                  </p>

                  <p className="mt-1 font-semibold text-slate-900">
                    #{safeText(
                      selectedScan.id
                    )}
                  </p>

                </div>


                <div>

                  <p className="text-xs text-slate-500">
                    Created
                  </p>

                  <p className="mt-1 font-semibold text-slate-900">
                    {formatDate(
                      selectedScan.created_at
                    )}
                  </p>

                </div>

              </div>

            </div>


            {/* =================================================
                TWO PRIMARY CLASSIFICATION CARDS
            ================================================= */}

            <div className="grid gap-5 lg:grid-cols-2">

              {/* FETAL PLANE */}

              <div className="rounded-2xl border border-slate-200 bg-white p-5">

                <div className="flex items-center justify-between gap-4">

                  <div className="flex items-center gap-3">

                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-50 text-teal-700">

                      <Activity
                        size={21}
                      />

                    </div>


                    <div>

                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                        Model 1
                      </p>


                      <h3 className="mt-1 font-semibold text-slate-900">
                        Fetal Plane Classification
                      </h3>

                    </div>

                  </div>


                  <span className="rounded-full bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-700">

                    Completed

                  </span>

                </div>


                <div className="mt-5 flex items-end justify-between gap-4">

                  <div>

                    <p className="text-xs text-slate-500">
                      Prediction
                    </p>


                    <p className="mt-1 text-xl font-semibold text-slate-900">
                      {fetalPrediction}
                    </p>

                  </div>


                  <div className="text-right">

                    <p className="text-xs text-slate-500">
                      Confidence
                    </p>


                    <p className="mt-1 text-2xl font-bold text-teal-700">

                      {fetalConfidence.toFixed(2)}%

                    </p>

                  </div>

                </div>


                <div className="mt-4">

                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">

                    <div
                      className="h-full rounded-full bg-teal-600 transition-all"
                      style={{
                        width:
                          `${Math.min(
                            Math.max(
                              fetalConfidence,
                              0
                            ),
                            100
                          )}%`,
                      }}
                    />

                  </div>


                  <div className="mt-2 flex justify-between text-[11px] text-slate-400">

                    <span>
                      0%
                    </span>

                    <span>
                      100%
                    </span>

                  </div>

                </div>

              </div>


              {/* BRAIN PLANE */}

              <div className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-5">

                <div className="flex items-center justify-between gap-4">

                  <div className="flex items-center gap-3">

                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">

                      <Brain
                        size={21}
                      />

                    </div>


                    <div>

                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                        Model 1.5
                      </p>


                      <h3 className="mt-1 font-semibold text-slate-900">
                        Brain Plane Classification
                      </h3>

                    </div>

                  </div>


                  <span
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                      brainAnalysisPerformed
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}
                  >

                    {brainAnalysisPerformed
                      ? 'Completed'
                      : 'Not applicable'}

                  </span>

                </div>


                <div className="mt-5 flex items-end justify-between gap-4">

                  <div>

                    <p className="text-xs text-slate-500">
                      Prediction
                    </p>


                    <p className="mt-1 text-xl font-semibold text-slate-900">

                      {brainPlaneAvailable
                        ? brainPrediction
                        : 'Not available'}

                    </p>

                  </div>


                  <div className="text-right">

                    <p className="text-xs text-slate-500">
                      Confidence
                    </p>


                    <p className="mt-1 text-2xl font-bold text-indigo-700">

                      {brainPlaneAvailable
                        ? `${brainConfidence.toFixed(2)}%`
                        : '—'}

                    </p>

                  </div>

                </div>


                {brainPlaneAvailable && (

                  <div className="mt-4">

                    <div className="h-2 overflow-hidden rounded-full bg-indigo-100">

                      <div
                        className="h-full rounded-full bg-indigo-600 transition-all"
                        style={{
                          width:
                            `${Math.min(
                              Math.max(
                                brainConfidence,
                                0
                              ),
                              100
                            )}%`,
                        }}
                      />

                    </div>


                    <div className="mt-2 flex justify-between text-[11px] text-slate-400">

                      <span>
                        0%
                      </span>

                      <span>
                        100%
                      </span>

                    </div>

                  </div>

                )}


                {!brainAnalysisPerformed && (

                  <div className="mt-4 flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-3 text-xs leading-5 text-amber-800">

                    <AlertTriangle
                      size={15}
                      className="mt-0.5 shrink-0"
                    />

                    <span>

                      Brain-plane confidence did not
                      reach the automatic analysis
                      threshold of{' '}

                      <strong>
                        {requiredBrainConfidence.toFixed(0)}%
                      </strong>.

                      Statistical screening may therefore
                      not have been performed.

                    </span>

                  </div>

                )}

              </div>

            </div>


            {/* =================================================
                STATISTICAL SCREENING
            ================================================= */}

            <div
              className={`overflow-hidden rounded-2xl border ${
                isStatisticalOutlier
                  ? 'border-amber-200 bg-amber-50/50'
                  : 'border-emerald-200 bg-emerald-50/50'
              }`}
            >

              <div className="p-5">

                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">

                  <div className="flex items-center gap-3">

                    <div
                      className={`flex h-11 w-11 items-center justify-center rounded-xl ${
                        isStatisticalOutlier
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >

                      {isStatisticalOutlier ? (

                        <AlertTriangle
                          size={21}
                        />

                      ) : (

                        <BarChart3
                          size={21}
                        />

                      )}

                    </div>


                    <div>

                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                        Model 2
                      </p>


                      <h3 className="mt-1 font-semibold text-slate-900">
                        Statistical Screening
                      </h3>

                    </div>

                  </div>


                  <span
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                      isStatisticalOutlier
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >

                    {statisticalStatus}

                  </span>

                </div>


                {outlier &&
                  Object.keys(
                    outlier
                  ).length > 0 ? (

                  <>

                    <div className="mt-5 grid gap-3 sm:grid-cols-3">

                      <div className="rounded-xl border border-slate-200 bg-white p-4">

                        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                          Anomaly Score
                        </p>


                        <p className="mt-2 text-xl font-semibold text-slate-900">

                          {Number.isFinite(
                            anomalyScore
                          )
                            ? anomalyScore.toFixed(4)
                            : '—'}

                        </p>

                      </div>


                      <div className="rounded-xl border border-slate-200 bg-white p-4">

                        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                          Reference Threshold
                        </p>


                        <p className="mt-2 text-xl font-semibold text-slate-900">

                          {Number.isFinite(
                            threshold
                          )
                            ? threshold.toFixed(4)
                            : '—'}

                        </p>

                      </div>


                      <div className="rounded-xl border border-slate-200 bg-white p-4">

                        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                          Threshold Ratio
                        </p>


                        <p className="mt-2 text-xl font-semibold text-slate-900">

                          {Number.isFinite(
                            thresholdRatioPercent
                          )
                            ? `${thresholdRatioPercent.toFixed(2)}%`
                            : '—'}

                        </p>


                        <p className="mt-1 text-[11px] text-slate-400">
                          Score / Threshold
                        </p>

                      </div>

                    </div>


                    {outlier.interpretation && (

                      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">

                        <div className="flex items-center gap-2">

                          <Info
                            size={16}
                            className="text-teal-600"
                          />

                          <p className="text-sm font-semibold text-slate-800">
                            Interpretation
                          </p>

                        </div>


                        <p className="mt-2 text-sm leading-6 text-slate-600">

                          {outlier.interpretation}

                        </p>

                      </div>

                    )}

                  </>

                ) : (

                  <div className="mt-5 rounded-xl border border-slate-200 bg-white p-4">

                    <p className="text-sm font-medium text-slate-700">
                      Statistical screening not available.
                    </p>


                    <p className="mt-1 text-xs leading-5 text-slate-500">

                      This stage may have been skipped
                      because the brain-plane confidence
                      was below the required threshold.

                    </p>

                  </div>

                )}


                <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3">

                  <AlertTriangle
                    size={15}
                    className="mt-0.5 shrink-0 text-amber-700"
                  />


                  <p className="text-xs leading-5 text-amber-800">

                    Statistical outlier analysis is
                    experimental and is not a clinically
                    validated fetal anomaly diagnosis.

                  </p>

                </div>

              </div>

            </div>


            {/* =================================================
                AI EXPLAINABILITY
            ================================================= */}

            <div className="rounded-2xl border border-slate-200 bg-white p-5">

              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">

                <div className="flex items-center gap-3">

                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-50 text-violet-700">

                    <Eye
                      size={21}
                    />

                  </div>


                  <div>

                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                      Model Explainability
                    </p>


                    <h3 className="mt-1 text-lg font-semibold text-slate-900">
                      AI Explainability — Grad-CAM
                    </h3>


                    <p className="mt-1 text-xs text-slate-500">

                      Visual explanation of model attention
                      for the fetal-plane classification.

                    </p>

                  </div>

                </div>


                <div className="rounded-full bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-700">

                  Experimental visualization

                </div>

              </div>


              {gradcamAvailable ? (

                <>

                  {/* EXPLAINABILITY METRICS */}

                  <div className="mt-5 grid gap-3 sm:grid-cols-3">

                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

                      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        Target Class
                      </p>


                      <p className="mt-2 font-semibold text-slate-900">

                        {safeText(
                          explainability?.target_class ||
                          fetalPrediction
                        )}

                      </p>

                    </div>


                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

                      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        Attention Score
                      </p>


                      <p className="mt-2 font-semibold text-slate-900">

                        {Number.isFinite(
                          attentionScore
                        )
                          ? attentionScore.toFixed(4)
                          : '—'}

                      </p>

                    </div>


                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

                      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        Attention Status
                      </p>


                      <p className="mt-2 font-semibold text-slate-900">

                        {safeText(
                          attentionStatus
                        )}

                      </p>

                    </div>

                  </div>


                  {/* ATTENTION INTERPRETATION */}

                  <div className="mt-4 rounded-xl bg-slate-50 p-4">

                    <div className="flex items-center gap-2">

                      <Info
                        size={16}
                        className="text-violet-600"
                      />

                      <p className="text-sm font-semibold text-slate-800">
                        Attention Interpretation
                      </p>

                    </div>


                    <p className="mt-2 text-sm leading-6 text-slate-600">

                      {attentionInterpretation}

                    </p>


                    {Number.isFinite(
                      attentionEntropy
                    ) && (

                      <p className="mt-2 text-xs text-slate-500">

                        Entropy:{' '}

                        <strong>
                          {attentionEntropy.toFixed(4)}
                        </strong>

                      </p>

                    )}

                  </div>


                  {/* GRAD-CAM IMAGES */}

                  <div className="mt-5 grid gap-5 lg:grid-cols-2">

                    {/* HEATMAP */}

                    <div className="overflow-hidden rounded-2xl border border-slate-200">

                      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">

                        <div className="flex items-center gap-2">

                          <ImageIcon
                            size={16}
                            className="text-violet-600"
                          />

                          <p className="text-sm font-semibold text-slate-800">
                            Grad-CAM Heatmap
                          </p>

                        </div>


                        <span className="text-[11px] text-slate-400">
                          AI evidence
                        </span>

                      </div>


                      <div className="bg-slate-950">

                        {gradcamHeatmapUrl &&
                        !heatmapError ? (

                          <img
                            src={gradcamHeatmapUrl}
                            alt="Grad-CAM attention heatmap"
                            className="h-72 w-full object-contain"
                            loading="lazy"
                            onError={() => {

                              console.error(
                                'Grad-CAM heatmap failed to load:',
                                gradcamHeatmapUrl
                              );

                              setHeatmapError(
                                true
                              );

                            }}
                          />

                        ) : (

                          <div className="flex h-72 items-center justify-center px-5 text-center text-sm text-slate-400">

                            {gradcamHeatmapUrl
                              ? 'Heatmap could not be loaded.'
                              : 'Heatmap unavailable.'}

                          </div>

                        )}

                      </div>


                      <div className="flex items-center justify-between px-4 py-3 text-[11px] text-slate-500">

                        <span>
                          Low Attention
                        </span>


                        <div className="mx-3 h-2 flex-1 rounded-full bg-gradient-to-r from-blue-500 via-yellow-400 to-red-500" />


                        <span>
                          High Attention
                        </span>

                      </div>

                    </div>


                    {/* OVERLAY */}

                    <div className="overflow-hidden rounded-2xl border border-slate-200">

                      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">

                        <div className="flex items-center gap-2">

                          <ImageIcon
                            size={16}
                            className="text-violet-600"
                          />

                          <p className="text-sm font-semibold text-slate-800">
                            Heatmap Overlay
                          </p>

                        </div>


                        <span className="text-[11px] text-slate-400">
                          Image + attention
                        </span>

                      </div>


                      <div className="bg-slate-950">

                        {gradcamOverlayUrl &&
                        !overlayError ? (

                          <img
                            src={gradcamOverlayUrl}
                            alt="Grad-CAM overlay on ultrasound"
                            className="h-72 w-full object-contain"
                            loading="lazy"
                            onError={() => {

                              console.error(
                                'Grad-CAM overlay failed to load:',
                                gradcamOverlayUrl
                              );

                              setOverlayError(
                                true
                              );

                            }}
                          />

                        ) : (

                          <div className="flex h-72 items-center justify-center px-5 text-center text-sm text-slate-400">

                            {gradcamOverlayUrl
                              ? 'Overlay could not be loaded.'
                              : 'Overlay unavailable.'}

                          </div>

                        )}

                      </div>


                      <div className="px-4 py-3 text-[11px] text-slate-500">

                        Heatmap overlaid on the original
                        ultrasound image.

                      </div>

                    </div>

                  </div>


                  {/* CLINICAL NOTE */}

                  <div className="mt-5 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">

                    <AlertTriangle
                      size={16}
                      className="mt-0.5 shrink-0 text-amber-700"
                    />


                    <p className="text-xs leading-5 text-amber-800">

                      Grad-CAM attention is an explainability
                      metric only. Highlighted regions indicate
                      model attention and are not anatomical
                      segmentation, clinical reliability scores,
                      or a medical diagnosis.

                    </p>

                  </div>

                </>

              ) : (

                <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-5">

                  <div className="flex items-start gap-3">

                    <Eye
                      size={20}
                      className="mt-0.5 shrink-0 text-slate-400"
                    />


                    <div>

                      <p className="font-semibold text-slate-700">
                        Grad-CAM unavailable
                      </p>


                      <p className="mt-1 text-sm leading-6 text-slate-500">

                        The selected scan does not currently
                        contain Grad-CAM explainability data.

                      </p>

                    </div>

                  </div>

                </div>

              )}

            </div>


            {/* =================================================
                PIPELINE SUMMARY
            ================================================= */}

            <div className="rounded-2xl border border-slate-200 p-5">

              <div className="flex items-center gap-3">

                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">

                  <ShieldCheck
                    size={21}
                  />

                </div>


                <div>

                  <h3 className="font-semibold text-slate-900">
                    Pipeline Summary
                  </h3>


                  <p className="text-sm text-slate-500">
                    AI processing stages completed for this scan.
                  </p>

                </div>

              </div>


              <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">

                {/* FETAL */}

                <div className="rounded-xl bg-slate-50 p-4">

                  <div className="flex items-center gap-2">

                    <Activity
                      size={16}
                      className="text-teal-600"
                    />

                    <p className="text-xs font-medium text-slate-500">
                      Fetal Plane
                    </p>

                  </div>


                  <p className="mt-2 font-semibold text-slate-900">
                    {fetalPrediction}
                  </p>


                  <p className="mt-1 text-xs text-teal-700">

                    {fetalConfidence.toFixed(2)}%

                  </p>

                </div>


                {/* BRAIN */}

                <div className="rounded-xl bg-slate-50 p-4">

                  <div className="flex items-center gap-2">

                    <Brain
                      size={16}
                      className="text-indigo-600"
                    />

                    <p className="text-xs font-medium text-slate-500">
                      Brain Plane
                    </p>

                  </div>


                  <p className="mt-2 font-semibold text-slate-900">

                    {brainAnalysisPerformed
                      ? brainPrediction
                      : 'Not applicable'}

                  </p>


                  {brainAnalysisPerformed && (

                    <p className="mt-1 text-xs text-indigo-700">

                      {brainConfidence.toFixed(2)}%

                    </p>

                  )}

                </div>


                {/* STATISTICAL */}

                <div className="rounded-xl bg-slate-50 p-4">

                  <div className="flex items-center gap-2">

                    <BarChart3
                      size={16}
                      className="text-emerald-600"
                    />

                    <p className="text-xs font-medium text-slate-500">
                      Statistical Screening
                    </p>

                  </div>


                  <p
                    className={`mt-2 font-semibold ${
                      isStatisticalOutlier
                        ? 'text-amber-700'
                        : 'text-emerald-700'
                    }`}
                  >

                    {statisticalStatus}

                  </p>


                  {hasStatisticalMetrics && (

                    <p className="mt-1 text-xs text-slate-500">

                      Score: {anomalyScore.toFixed(4)}

                    </p>

                  )}

                </div>


                {/* EXPLAINABILITY */}

                <div className="rounded-xl bg-slate-50 p-4">

                  <div className="flex items-center gap-2">

                    <Eye
                      size={16}
                      className="text-violet-600"
                    />

                    <p className="text-xs font-medium text-slate-500">
                      Explainability
                    </p>

                  </div>


                  <p className="mt-2 font-semibold text-slate-900">

                    {gradcamAvailable
                      ? 'Grad-CAM Generated'
                      : 'Not available'}

                  </p>


                  {gradcamAvailable && (

                    <p className="mt-1 text-xs text-violet-700">
                      Heatmap + Overlay
                    </p>

                  )}

                </div>

              </div>


              {/* PIPELINE MESSAGE */}

              <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">

                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Pipeline Status
                </p>


                <p className="mt-1 text-sm font-semibold text-slate-800">
                  {pipelineStatus}
                </p>


                <p className="mt-1 text-xs leading-5 text-slate-500">
                  {pipelineMessage}
                </p>

              </div>

            </div>


            {/* =================================================
                FINAL DISCLAIMER
            ================================================= */}

            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">

              <div className="flex items-start gap-3">

                <AlertTriangle
                  size={20}
                  className="mt-0.5 shrink-0 text-amber-600"
                />


                <div>

                  <p className="font-semibold text-amber-900">
                    Important Clinical Note
                  </p>


                  <p className="mt-1 text-sm leading-6 text-amber-800">

                    FetalAI provides experimental
                    AI-assisted analysis and statistical
                    screening results. These results are
                    not a clinically validated diagnosis
                    and should not replace evaluation by
                    a qualified medical professional.

                  </p>


                  <p className="mt-2 text-sm leading-6 text-amber-800">

                    Grad-CAM attention metrics are
                    explainability metrics only and should
                    not be interpreted as clinical
                    reliability scores or medical
                    diagnoses.

                  </p>

                </div>

              </div>

            </div>


            {/* =================================================
                FOOTER
            ================================================= */}

            <div className="flex flex-col justify-between gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:items-center">

              <div className="flex items-center gap-2 text-xs text-slate-400">

                <ShieldCheck
                  size={15}
                />

                FetalAI v2.4 • For research &
                screening use only

              </div>


              <Button
                type="button"
                onClick={generatePdf}
                disabled={
                  generatingPdf ||
                  !selectedScan
                }
              >

                {generatingPdf ? (

                  <RefreshCw
                    size={17}
                    className="mr-2 animate-spin"
                  />

                ) : (

                  <Download
                    size={17}
                    className="mr-2"
                  />

                )}


                {generatingPdf
                  ? 'Generating PDF...'
                  : 'Download Full Report'}

              </Button>

            </div>

          </div>

        </Card>

      )}

    </div>

  );
}


export default ReportsPage;