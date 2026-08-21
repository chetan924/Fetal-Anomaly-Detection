import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  Upload,
  FileImage,
  X,
  Brain,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  UserRound,
  RefreshCw,
  Eye,
  Search,
  ChevronDown,
  Check,
} from 'lucide-react';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

import {
  getPatients,
  uploadScan,
} from '../services/api';

import {
  addNotification,
} from '../services/notifications';


// ============================================================
// COMPONENT
// ============================================================

function NewScanPage() {

  const navigate = useNavigate();

  // ==========================================================
  // STATE
  // ==========================================================

  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState('');

  const [patientDropdownOpen, setPatientDropdownOpen] =
    useState(false);

  const [patientSearch, setPatientSearch] =
    useState('');

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');

  const [loadingPatients, setLoadingPatients] =
    useState(true);

  const [analyzing, setAnalyzing] =
    useState(false);

  const [progress, setProgress] =
    useState(0);

  const [error, setError] =
    useState('');

  const [result, setResult] =
    useState(null);

  // ==========================================================
  // GRAD-CAM IMAGE ERROR STATE
  // ==========================================================

  const [heatmapError, setHeatmapError] =
    useState(false);

  const [overlayError, setOverlayError] =
    useState(false);


  // ==========================================================
  // LOAD PATIENTS
  // ==========================================================

  useEffect(() => {

    let mounted = true;

    const loadPatients = async () => {

      try {

        setLoadingPatients(true);
        setError('');

        const response = await getPatients();

        const data =
          Array.isArray(response)
            ? response
            : response?.patients || [];

        if (!mounted) {
          return;
        }

        setPatients(data);

        if (data.length > 0) {

          const firstPatient = data[0];

          setPatientId(
            firstPatient.patient_id ??
            firstPatient.id ??
            ''
          );

        }

      } catch (err) {

        if (!mounted) {
          return;
        }

        setError(
          getErrorMessage(
            err,
            'Failed to load patients.'
          )
        );

      } finally {

        if (mounted) {
          setLoadingPatients(false);
        }

      }

    };

    loadPatients();

    return () => {
      mounted = false;
    };

  }, []);


  // ==========================================================
  // PATIENT DROPDOWN — OUTSIDE CLICK
  // ==========================================================

  useEffect(() => {

    const handleOutsideClick = (event) => {

      if (
        !event.target.closest(
          '[data-patient-dropdown]'
        )
      ) {

        setPatientDropdownOpen(false);

      }

    };

    document.addEventListener(
      'mousedown',
      handleOutsideClick
    );

    return () => {

      document.removeEventListener(
        'mousedown',
        handleOutsideClick
      );

    };

  }, []);


  // ==========================================================
  // CLEAN PREVIEW URL
  // ==========================================================

  useEffect(() => {

    return () => {

      if (preview) {
        URL.revokeObjectURL(preview);
      }

    };

  }, [preview]);


  // ==========================================================
  // ERROR MESSAGE HELPER
  // ==========================================================

  function getErrorMessage(err, fallback) {

    const detail =
      err?.response?.data?.detail;

    if (Array.isArray(detail)) {

      return detail
        .map((item) => {

          if (
            item &&
            typeof item === 'object'
          ) {

            const location =
              Array.isArray(item.loc)
                ? item.loc.join('.')
                : '';

            const message =
              item.msg ||
              'Invalid value';

            return location
              ? `${location}: ${message}`
              : message;

          }

          return String(item);

        })
        .join(', ');

    }

    if (typeof detail === 'string') {
      return detail;
    }

    if (err?.response?.data?.message) {
      return err.response.data.message;
    }

    if (err?.message) {
      return err.message;
    }

    return fallback;
  }


  // ==========================================================
  // FILE VALIDATION
  // ==========================================================

  const handleFileChange = (selectedFile) => {

    if (!selectedFile) {
      return;
    }

    setError('');
    setResult(null);
    setProgress(0);

    setHeatmapError(false);
    setOverlayError(false);

    const allowedTypes = [
      'image/jpeg',
      'image/png',
      'image/webp',
    ];

    if (!allowedTypes.includes(selectedFile.type)) {

      setError(
        'Unsupported image format. Please select JPG, PNG or WEBP.'
      );

      return;
    }

    const maxFileSize =
      20 * 1024 * 1024;

    if (selectedFile.size > maxFileSize) {

      setError(
        'Image size must be 20 MB or smaller.'
      );

      return;
    }

    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setFile(selectedFile);

    const objectUrl =
      URL.createObjectURL(selectedFile);

    setPreview(objectUrl);
  };


  // ==========================================================
  // FILE INPUT
  // ==========================================================

  const handleInputChange = (event) => {

    const selectedFile =
      event.target.files?.[0];

    handleFileChange(selectedFile);

    event.target.value = '';
  };


  // ==========================================================
  // REMOVE FILE
  // ==========================================================

  const removeFile = () => {

    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setFile(null);
    setPreview('');
    setResult(null);
    setProgress(0);
    setError('');

    setHeatmapError(false);
    setOverlayError(false);
  };


  // ==========================================================
  // ANALYZE
  // ==========================================================

  const handleAnalyze = async () => {

    // --------------------------------------------------------
    // PATIENT VALIDATION
    // --------------------------------------------------------

    if (!patientId) {

      setError(
        'Please select a patient.'
      );

      return;
    }


    // --------------------------------------------------------
    // FILE VALIDATION
    // --------------------------------------------------------

    if (!file) {

      setError(
        'Please select an ultrasound image.'
      );

      return;
    }


    setError('');
    setResult(null);
    setAnalyzing(true);
    setProgress(0);

    setHeatmapError(false);
    setOverlayError(false);


    try {

      // ======================================================
      // UPLOAD + AI ANALYSIS
      // ======================================================

      const response =
        await uploadScan(
          patientId,
          file,
          (event) => {

            if (event.total) {

              const uploadProgress =
                Math.round(
                  (
                    event.loaded /
                    event.total
                  ) * 100
                );

              setProgress(
                Math.min(
                  uploadProgress,
                  100
                )
              );

            }

          }
        );


      // ======================================================
      // SAVE RESULT
      // ======================================================

      setResult(response);
      setProgress(100);


      // ======================================================
      // EXTRACT RESPONSE DATA
      // ======================================================

      const scanId =
        response?.scan_id ??
        response?.scan?.id ??
        response?.id ??
        'Unknown';


      const selectedPatient =
        patients.find(
          (patient) =>
            String(
              patient.patient_id ??
              patient.id ??
              ''
            ) ===
            String(patientId)
        );


      const patientName =
        response?.patient?.patient_name ??
        response?.patient?.full_name ??
        response?.scan?.patient_name ??
        selectedPatient?.full_name ??
        selectedPatient?.name ??
        'Selected patient';


      const responseAnalysis =
        response?.analysis ||
        response?.scan?.analysis_result ||
        response?.analysis_result ||
        null;


      const predictedPlane =
        responseAnalysis
          ?.fetal_plane
          ?.predicted_class ??
        'Unknown plane';


      // ======================================================
      // SUCCESS NOTIFICATION
      // ======================================================

      addNotification({

        type: 'success',

        title:
          'Scan analysis completed',

        message:
          `Scan #${scanId} for ${patientName} ` +
          `was successfully analyzed. ` +
          `Fetal plane: ${predictedPlane}.`,

      });


      // ======================================================
      // STATISTICAL OUTLIER NOTIFICATION
      // ======================================================

      const outlierResult =
        responseAnalysis
          ?.outlier_analysis;


      const outlierStatus =
        String(
          outlierResult?.status || ''
        ).toLowerCase();


      const isOutlier =
        outlierResult?.is_outlier === true ||
        outlierStatus.includes('outlier') ||
        outlierStatus.includes('flag');


      if (
        outlierResult &&
        isOutlier
      ) {

        addNotification({

          type: 'warning',

          title:
            'Statistical screening flagged',

          message:
            `Scan #${scanId} produced a ` +
            `statistical screening result that ` +
            `may require clinical review. ` +
            `This is not a clinical diagnosis.`,

        });

      }


    } catch (err) {

      console.error(
        'Ultrasound analysis error:',
        err
      );


      const errorMessage =
        getErrorMessage(
          err,
          'Ultrasound analysis failed. Please try again.'
        );


      addNotification({

        type: 'error',

        title:
          'Ultrasound analysis failed',

        message:
          errorMessage,

      });


      setError(errorMessage);


    } finally {

      setAnalyzing(false);

    }

  };


  // ==========================================================
  // EXTRACT ANALYSIS
  // ==========================================================

  const analysis =
    result?.analysis ||
    result?.scan?.analysis_result ||
    result?.analysis_result ||
    null;

  const fetalPlane =
    analysis?.fetal_plane || null;

  const brainPlane =
    analysis?.brain_plane || null;

  const outlier =
    analysis?.outlier_analysis || null;


  // ==========================================================
  // GRAD-CAM / AI EXPLAINABILITY
  // ==========================================================

  const explainability =
    analysis?.explainability ||
    analysis?.gradcam ||
    result?.explainability ||
    result?.gradcam ||
    result?.scan?.explainability ||
    result?.scan?.analysis_result?.explainability ||
    result?.scan?.analysis_result?.gradcam ||
    result?.analysis_result?.explainability ||
    result?.analysis_result?.gradcam ||
    null;


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
  // GRAD-CAM URL HELPER
  // ==========================================================

  const getStorageUrl = (path) => {

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
    // ABSOLUTE URL
    // --------------------------------------------------------

    if (
      normalizedPath.startsWith('http://') ||
      normalizedPath.startsWith('https://')
    ) {

      return normalizedPath;

    }


    // --------------------------------------------------------
    // REMOVE LEADING SLASH
    // --------------------------------------------------------

    normalizedPath =
      normalizedPath.replace(
        /^\/+/,
        ''
      );


    // --------------------------------------------------------
    // REMOVE /api PREFIX IF PRESENT
    // --------------------------------------------------------

    normalizedPath =
      normalizedPath.replace(
        /^api\//i,
        ''
      );


    // --------------------------------------------------------
    // DETECT STORAGE PATH
    // --------------------------------------------------------

    const storageIndex =
      normalizedPath
        .toLowerCase()
        .indexOf('storage/');


    if (storageIndex >= 0) {

      normalizedPath =
        normalizedPath.substring(
          storageIndex
        );

    }


    // --------------------------------------------------------
    // ENSURE STORAGE PREFIX
    // --------------------------------------------------------

    if (
      !normalizedPath
        .toLowerCase()
        .startsWith('storage/')
    ) {

      normalizedPath =
        `storage/${normalizedPath}`;

    }


    // --------------------------------------------------------
    // REMOVE /api
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
  // GRAD-CAM PATHS
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


  // ==========================================================
  // GRAD-CAM AVAILABLE
  // ==========================================================

  const gradcamAvailable =
    Boolean(
      explainability &&
      (
        explainability.status === 'available' ||
        gradcamHeatmapUrl ||
        gradcamOverlayUrl
      )
    );


  // ==========================================================
  // DERIVED BRAIN STATUS
  // ==========================================================

  const brainConfidence =
    brainPlane
      ? Number(
          brainPlane.confidence_percent ??
          (
            Number(
              brainPlane.confidence
            ) * 100
          )
        )
      : 0;


  const requiredBrainConfidence =
    Number(
      analysis?.required_confidence ??
      70
    );


  const brainAnalysisPerformed =
    analysis?.brain_analysis_performed === true;


  const brainPlaneAvailable =
    Boolean(brainPlane);


  // ==========================================================
  // DERIVED STATISTICAL STATUS
  // ==========================================================

  const outlierStatus =
    String(
      outlier?.status || ''
    ).toLowerCase();


  const statisticalOutlier =
    outlier?.is_outlier === true ||
    outlierStatus.includes('outlier') ||
    outlierStatus.includes('flag');


  const statisticalScore =
    outlier?.anomaly_score;


  const statisticalThreshold =
    outlier?.threshold;


  const statisticalRatio =
    outlier?.threshold_ratio;


  // ==========================================================
  // STATISTICAL METRICS
  // ==========================================================

  const parsedStatisticalScore =
    Number(
      statisticalScore
    );


  const parsedStatisticalThreshold =
    Number(
      statisticalThreshold
    );


  const parsedStatisticalRatio =
    Number(
      statisticalRatio
    );


  const hasStatisticalMetrics =
    Number.isFinite(
      parsedStatisticalScore
    ) &&
    Number.isFinite(
      parsedStatisticalThreshold
    ) &&
    parsedStatisticalThreshold > 0;


  const statisticalRatioPercent =
    Number.isFinite(
      parsedStatisticalRatio
    )
      ? (
          parsedStatisticalRatio <= 1
            ? parsedStatisticalRatio * 100
            : parsedStatisticalRatio
        )
      : hasStatisticalMetrics
        ? (
            parsedStatisticalScore /
            parsedStatisticalThreshold
          ) * 100
        : 0;


  const scoreVsThresholdPercent =
    hasStatisticalMetrics
      ? (
          parsedStatisticalScore /
          parsedStatisticalThreshold
        ) * 100
      : 0;


  const safeScoreVsThresholdPercent =
    Math.min(
      Math.max(
        scoreVsThresholdPercent,
        0
      ),
      100
    );


  // ==========================================================
  // SAFE CONFIDENCE VALUES
  // ==========================================================

  const fetalConfidenceRaw =
    fetalPlane?.confidence_percent ??
    (
      Number(
        fetalPlane?.confidence
      ) * 100
    );


  const fetalConfidence =
    Number.isFinite(
      Number(fetalConfidenceRaw)
    )
      ? Number(fetalConfidenceRaw)
      : 0;


  const brainConfidenceSafe =
    Number.isFinite(
      brainConfidence
    )
      ? brainConfidence
      : 0;


  const explainabilityConfidence =
    explainability?.confidence_percent ??
    fetalConfidence;


  const safeExplainabilityConfidence =
    Number.isFinite(
      Number(explainabilityConfidence)
    )
      ? Number(explainabilityConfidence)
      : 0;


  // ==========================================================
  // PATIENT DROPDOWN DATA
  // ==========================================================

  const filteredPatients =
    patients.filter((patient) => {

      const search =
        patientSearch
          .trim()
          .toLowerCase();

      if (!search) {
        return true;
      }

      const patientCode =
        String(
          patient.patient_id ??
          patient.id ??
          ''
        ).toLowerCase();

      const patientName =
        String(
          patient.full_name ??
          patient.name ??
          ''
        ).toLowerCase();

      return (
        patientCode.includes(search) ||
        patientName.includes(search)
      );

    });


  const selectedPatient =
    patients.find(
      (patient) =>
        String(
          patient.patient_id ??
          patient.id ??
          ''
        ) ===
        String(patientId)
    );


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="space-y-6 p-6">

      {/* ====================================================
          HEADER
      ==================================================== */}

      <div>

        <h1 className="text-2xl font-semibold text-slate-900">
          New Scan
        </h1>

        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          Upload an ultrasound image for
          AI-assisted fetal plane and brain
          analysis.
        </p>

      </div>


      {/* ====================================================
          ERROR
      ==================================================== */}

      {error && (

        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
        >

          <AlertTriangle
            size={18}
            className="mt-0.5 shrink-0"
          />

          <span>
            {error}
          </span>

        </div>

      )}


      {/* ====================================================
          MAIN GRID
      ==================================================== */}

      <div className="grid gap-6 lg:grid-cols-2">

        {/* ==================================================
            LEFT — UPLOAD
        ================================================== */}

        <Card
          title="Upload Ultrasound"
          subtitle="Select a patient and upload an ultrasound image."
        >

          <div className="mt-5 space-y-5">

            {/* PATIENT */}

            <div>

              <label
                htmlFor="patient"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Patient
              </label>


              <div
                className="relative"
                data-patient-dropdown
              >

                {/* ==================================================
                    SELECT BUTTON
                ================================================== */}

                <button
                  id="patient"
                  type="button"
                  disabled={
                    loadingPatients ||
                    analyzing ||
                    patients.length === 0
                  }
                  onClick={() => {

                    setPatientDropdownOpen(
                      (previous) => !previous
                    );

                    setPatientSearch('');

                  }}
                  className={`
                    flex
                    w-full
                    items-center
                    gap-3
                    rounded-xl
                    border
                    bg-white
                    px-4
                    py-3
                    text-left
                    outline-none
                    transition-all
                    duration-200
                    ${
                      patientDropdownOpen
                        ? 'border-teal-500 ring-2 ring-teal-100'
                        : 'border-slate-300 hover:border-teal-400'
                    }
                    ${
                      loadingPatients ||
                      analyzing ||
                      patients.length === 0
                        ? 'cursor-not-allowed bg-slate-100 opacity-70'
                        : 'cursor-pointer'
                    }
                  `}
                >

                  <div
                    className={`
                      flex
                      h-9
                      w-9
                      shrink-0
                      items-center
                      justify-center
                      rounded-lg
                      ${
                        selectedPatient
                          ? 'bg-teal-50 text-teal-700'
                          : 'bg-slate-100 text-slate-400'
                      }
                    `}
                  >

                    <UserRound
                      size={18}
                    />

                  </div>


                  <div className="min-w-0 flex-1">

                    {selectedPatient ? (

                      <>

                        <p className="truncate text-sm font-semibold text-slate-800">

                          {selectedPatient.patient_id ??
                            selectedPatient.id}

                        </p>


                        <p className="truncate text-xs text-slate-500">

                          {selectedPatient.full_name ??
                            selectedPatient.name ??
                            'Unnamed patient'}

                        </p>

                      </>

                    ) : (

                      <p className="text-sm text-slate-400">

                        {loadingPatients
                          ? 'Loading patients...'
                          : patients.length === 0
                            ? 'No patients available'
                            : 'Select patient'}

                      </p>

                    )}

                  </div>


                  <ChevronDown
                    size={18}
                    className={`
                      shrink-0
                      text-slate-400
                      transition-transform
                      duration-200
                      ${
                        patientDropdownOpen
                          ? 'rotate-180 text-teal-600'
                          : ''
                      }
                    `}
                  />

                </button>


                {/* ==================================================
                    DROPDOWN
                ================================================== */}

                {patientDropdownOpen &&
                  !loadingPatients &&
                  patients.length > 0 && (

                    <div
                      className="
                        absolute
                        left-0
                        right-0
                        top-full
                        z-50
                        mt-2
                        overflow-hidden
                        rounded-2xl
                        border
                        border-slate-200
                        bg-white
                        shadow-xl
                        shadow-slate-900/10
                      "
                    >

                      {/* SEARCH */}

                      <div className="border-b border-slate-100 p-3">

                        <div className="relative">

                          <Search
                            size={17}
                            className="
                              pointer-events-none
                              absolute
                              left-3
                              top-1/2
                              -translate-y-1/2
                              text-slate-400
                            "
                          />


                          <input
                            type="text"
                            value={patientSearch}
                            onChange={(event) =>
                              setPatientSearch(
                                event.target.value
                              )
                            }
                            placeholder="Search patients..."
                            autoFocus
                            className="
                              w-full
                              rounded-xl
                              border
                              border-slate-200
                              bg-slate-50
                              py-2.5
                              pl-10
                              pr-3
                              text-sm
                              text-slate-800
                              outline-none
                              transition
                              placeholder:text-slate-400
                              focus:border-teal-400
                              focus:bg-white
                              focus:ring-2
                              focus:ring-teal-100
                            "
                          />

                        </div>

                      </div>


                      {/* PATIENT LIST */}

                      <div
                        className="
                          max-h-64
                          overflow-y-auto
                          p-2
                        "
                      >

                        {filteredPatients.length > 0 ? (

                          filteredPatients.map(
                            (patient) => {

                              const value =
                                patient.patient_id ??
                                patient.id ??
                                '';

                              const isSelected =
                                String(value) ===
                                String(patientId);


                              return (

                                <button
                                  key={value}
                                  type="button"
                                  onClick={() => {

                                    setPatientId(
                                      value
                                    );

                                    setPatientDropdownOpen(
                                      false
                                    );

                                    setPatientSearch('');

                                    setError('');

                                  }}
                                  className={`
                                    group
                                    flex
                                    w-full
                                    items-center
                                    gap-3
                                    rounded-xl
                                    px-3
                                    py-3
                                    text-left
                                    transition
                                    ${
                                      isSelected
                                        ? 'bg-teal-50'
                                        : 'hover:bg-slate-50'
                                    }
                                  `}
                                >

                                  <div
                                    className={`
                                      flex
                                      h-10
                                      w-10
                                      shrink-0
                                      items-center
                                      justify-center
                                      rounded-xl
                                      text-sm
                                      font-semibold
                                      ${
                                        isSelected
                                          ? 'bg-teal-100 text-teal-700'
                                          : 'bg-slate-100 text-slate-500 group-hover:bg-teal-50 group-hover:text-teal-600'
                                      }
                                    `}
                                  >

                                    <UserRound
                                      size={18}
                                    />

                                  </div>


                                  <div className="min-w-0 flex-1">

                                    <p
                                      className={`
                                        truncate
                                        text-sm
                                        font-semibold
                                        ${
                                          isSelected
                                            ? 'text-teal-800'
                                            : 'text-slate-800'
                                        }
                                      `}
                                    >

                                      {patient.patient_id ??
                                        patient.id}

                                    </p>


                                    <p className="truncate text-xs text-slate-500">

                                      {patient.full_name ??
                                        patient.name ??
                                        'Unnamed patient'}

                                    </p>

                                  </div>


                                  {isSelected && (

                                    <div
                                      className="
                                        flex
                                        h-7
                                        w-7
                                        shrink-0
                                        items-center
                                        justify-center
                                        rounded-full
                                        bg-teal-600
                                        text-white
                                      "
                                    >

                                      <Check
                                        size={15}
                                      />

                                    </div>

                                  )}

                                </button>

                              );

                            }
                          )

                        ) : (

                          <div
                            className="
                              px-4
                              py-8
                              text-center
                            "
                          >

                            <Search
                              size={24}
                              className="
                                mx-auto
                                text-slate-300
                              "
                            />


                            <p className="
                              mt-2
                              text-sm
                              font-medium
                              text-slate-600
                            ">
                              No patients found
                            </p>


                            <p className="
                              mt-1
                              text-xs
                              text-slate-400
                            ">
                              Try searching with another name or ID.
                            </p>

                          </div>

                        )}

                      </div>

                    </div>

                  )}

              </div>


              {!loadingPatients &&
                patients.length === 0 && (

                  <p className="mt-2 text-xs text-amber-600">
                    Create a patient first before
                    starting a scan.
                  </p>

                )}

            </div>


            {/* FILE UPLOAD */}

            {!file ? (

              <label
                htmlFor="ultrasound-file"
                className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center transition hover:border-teal-400 hover:bg-teal-50"
              >

                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-100 text-teal-700">

                  <Upload size={26} />

                </div>


                <p className="mt-4 text-sm font-semibold text-slate-800">
                  Upload ultrasound image
                </p>


                <p className="mt-1 text-xs text-slate-500">
                  JPG, PNG or WEBP • Maximum 20 MB
                </p>


                <input
                  id="ultrasound-file"
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                  onChange={handleInputChange}
                  className="hidden"
                  disabled={analyzing}
                />

              </label>

            ) : (

              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">

                <div className="relative">

                  <img
                    src={preview}
                    alt="Selected ultrasound preview"
                    className="h-72 w-full bg-slate-950 object-contain"
                  />


                  <button
                    type="button"
                    onClick={removeFile}
                    disabled={analyzing}
                    className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-full bg-white/95 text-slate-700 shadow transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label="Remove selected image"
                  >

                    <X size={18} />

                  </button>

                </div>


                <div className="flex items-center gap-3 p-4">

                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700">

                    <FileImage size={20} />

                  </div>


                  <div className="min-w-0">

                    <p className="truncate text-sm font-semibold text-slate-800">
                      {file.name}
                    </p>


                    <p className="text-xs text-slate-500">

                      {(
                        file.size /
                        1024 /
                        1024
                      ).toFixed(2)}{' '}
                      MB

                    </p>

                  </div>

                </div>

              </div>

            )}


            {/* PROGRESS */}

            {analyzing && (

              <div>

                <div className="mb-2 flex items-center justify-between text-xs">

                  <span className="font-medium text-slate-700">
                    Uploading and analyzing...
                  </span>


                  <span className="text-slate-500">
                    {progress}%
                  </span>

                </div>


                <div className="h-2 overflow-hidden rounded-full bg-slate-200">

                  <div
                    className="h-full rounded-full bg-teal-600 transition-all duration-300"
                    style={{
                      width: `${progress}%`,
                    }}
                  />

                </div>

              </div>

            )}


            {/* ANALYZE BUTTON */}

            <Button
              type="button"
              onClick={handleAnalyze}
              disabled={
                analyzing ||
                !file ||
                !patientId ||
                loadingPatients
              }
              className="w-full"
            >

              {analyzing ? (

                <>

                  <Loader2
                    size={18}
                    className="mr-2 animate-spin"
                  />

                  Analyzing ultrasound...

                </>

              ) : (

                <>

                  <Activity
                    size={18}
                    className="mr-2"
                  />

                  Analyze Ultrasound

                </>

              )}

            </Button>

          </div>

        </Card>


        {/* ==================================================
            RIGHT — AI ANALYSIS
        ================================================== */}

        <Card
          title="AI Analysis"
          subtitle={
            result
              ? 'Analysis completed successfully.'
              : 'Results will appear here after analysis.'
          }
        >

          {!result ? (

            <div className="flex min-h-[420px] flex-col items-center justify-center text-center">

              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">

                <Brain size={30} />

              </div>


              <p className="mt-4 text-sm font-semibold text-slate-700">
                Awaiting ultrasound
              </p>


              <p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">

                Upload an image and start AI
                analysis to see fetal plane,
                brain plane and statistical
                outlier results.

              </p>

            </div>

          ) : (

            <div className="mt-5 space-y-4">

              {/* =================================================
                  RESULT SUMMARY
              ================================================= */}

              <div className="rounded-2xl border border-teal-200 bg-teal-50/40 p-4">

                <div className="flex items-start gap-3">

                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-100 text-teal-700">

                    <CheckCircle2 size={20} />

                  </div>


                  <div className="min-w-0">

                    <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
                      AI Analysis Complete
                    </p>


                    <p className="mt-1 text-sm font-semibold text-slate-900">

                      Primary fetal-plane classification completed.

                    </p>


                    <p className="mt-1 text-xs leading-5 text-slate-600">

                      The following sections show the model
                      outputs in analysis order.

                    </p>

                  </div>

                </div>

              </div>


              {/* =================================================
                  MODEL 1 — FETAL PLANE
              ================================================= */}

              <div className="rounded-2xl border border-slate-200 bg-white p-4">

                <div className="flex items-center justify-between gap-4">

                  <div className="flex min-w-0 items-center gap-3">

                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700">

                      <Activity size={20} />

                    </div>


                    <div className="min-w-0">

                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                        Model 1
                      </p>


                      <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                        Fetal Plane
                      </p>


                      <p className="mt-1 truncate text-lg font-semibold text-slate-900">

                        {fetalPlane?.predicted_class ||
                          'Unknown'}

                      </p>

                    </div>

                  </div>


                  <div className="shrink-0 rounded-xl bg-teal-50 px-3 py-2 text-sm font-bold text-teal-700">

                    {fetalConfidence.toFixed(2)}%

                  </div>

                </div>


                {analysis?.message && (

                  <p className="mt-3 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500">

                    {analysis.message}

                  </p>

                )}

              </div>


              {/* =================================================
                  MODEL 1.5 — BRAIN PLANE
              ================================================= */}

              {brainPlaneAvailable && (

                <div
                  className={`rounded-2xl border p-4 ${
                    brainAnalysisPerformed
                      ? 'border-indigo-200 bg-indigo-50/50'
                      : 'border-amber-200 bg-amber-50/50'
                  }`}
                >

                  <div className="flex items-center gap-3">

                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                        brainAnalysisPerformed
                          ? 'bg-indigo-100 text-indigo-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}
                    >

                      <Brain size={20} />

                    </div>


                    <div>

                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                        Model 1.5
                      </p>


                      <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                        Brain Plane
                      </p>


                      <p className="mt-1 font-semibold text-slate-900">

                        {brainPlane.predicted_class ||
                          'Unknown'}

                      </p>

                    </div>

                  </div>


                  <div className="mt-4 flex items-center justify-between border-t border-slate-200 pt-3">

                    <span className="text-sm text-slate-600">
                      Confidence
                    </span>


                    <span
                      className={`font-semibold ${
                        brainAnalysisPerformed
                          ? 'text-indigo-700'
                          : 'text-amber-700'
                      }`}
                    >

                      {brainConfidenceSafe.toFixed(2)}%

                    </span>

                  </div>


                  {brainAnalysisPerformed ? (

                    <div className="mt-3 flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-700">

                      <CheckCircle2
                        size={15}
                        className="shrink-0"
                      />

                      Brain-plane confidence was sufficient
                      for statistical screening.

                    </div>

                  ) : (

                    <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">

                      <AlertTriangle
                        size={15}
                        className="mt-0.5 shrink-0"
                      />

                      <span>

                        Brain-plane confidence is below
                        the automatic analysis threshold.

                        {' '}

                        Required confidence:{' '}

                        <strong>
                          {requiredBrainConfidence.toFixed(0)}%
                        </strong>.

                        {' '}

                        Statistical screening was
                        therefore not performed.

                      </span>

                    </div>

                  )}

                </div>

              )}


              {/* =================================================
                  BRAIN PLANE NOT AVAILABLE
              ================================================= */}

              {analysis &&
                !brainPlaneAvailable &&
                analysis.brain_analysis_performed ===
                  false && (

                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">

                    <div className="flex items-start gap-3">

                      <Brain
                        size={20}
                        className="mt-0.5 shrink-0 text-slate-400"
                      />


                      <div>

                        <p className="text-sm font-semibold text-slate-700">
                          Brain-specific analysis not performed
                        </p>


                        <p className="mt-1 text-xs leading-5 text-slate-500">

                          The uploaded image was not
                          classified as a fetal-brain
                          plane, so brain-specific
                          analysis was not performed.

                        </p>

                      </div>

                    </div>

                  </div>

                )}


              {/* =================================================
                  MODEL 2 — STATISTICAL SCREENING
              ================================================= */}

              {outlier && (

                <div
                  className={`overflow-hidden rounded-2xl border ${
                    statisticalOutlier
                      ? 'border-amber-200 bg-amber-50'
                      : 'border-emerald-200 bg-emerald-50'
                  }`}
                >

                  <div className="flex items-start justify-between gap-4 p-4">

                    <div className="flex items-center gap-3">

                      <div
                        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${
                          statisticalOutlier
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-emerald-100 text-emerald-700'
                        }`}
                      >

                        {statisticalOutlier ? (
                          <AlertTriangle size={21} />
                        ) : (
                          <CheckCircle2 size={21} />
                        )}

                      </div>


                      <div>

                        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                          Model 2
                        </p>


                        <p className="mt-1 text-base font-semibold text-slate-900">
                          Statistical Screening
                        </p>

                      </div>

                    </div>


                    <span
                      className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${
                        statisticalOutlier
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >

                      {statisticalOutlier
                        ? 'Potential outlier'
                        : 'In-distribution'}

                    </span>

                  </div>


                  <div className="px-4 pb-4">

                    <div
                      className={`rounded-xl border px-3 py-3 ${
                        statisticalOutlier
                          ? 'border-amber-200 bg-white/60'
                          : 'border-emerald-200 bg-white/60'
                      }`}
                    >

                      <p
                        className={`text-sm font-medium ${
                          statisticalOutlier
                            ? 'text-amber-900'
                            : 'text-emerald-900'
                        }`}
                      >

                        {statisticalOutlier
                          ? 'The statistical model detected a result outside its learned reference range.'
                          : 'The statistical model found this result within its learned reference range.'}

                      </p>


                      <p className="mt-1 text-xs leading-5 text-slate-600">

                        {statisticalOutlier
                          ? 'This result may require additional clinical review.'
                          : 'No statistical outlier was identified by this screening model.'}

                      </p>

                    </div>

                  </div>


                  {/* METRICS */}

                  <div className="grid gap-3 px-4 pb-4 sm:grid-cols-3">

                    <div className="rounded-xl border border-slate-200 bg-white p-3">

                      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        Anomaly Score
                      </p>


                      <p className="mt-2 text-xl font-semibold text-slate-900">

                        {hasStatisticalMetrics
                          ? parsedStatisticalScore.toFixed(4)
                          : 'N/A'}

                      </p>

                    </div>


                    <div className="rounded-xl border border-slate-200 bg-white p-3">

                      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        Threshold
                      </p>


                      <p className="mt-2 text-xl font-semibold text-slate-900">

                        {hasStatisticalMetrics
                          ? parsedStatisticalThreshold.toFixed(4)
                          : 'N/A'}

                      </p>

                    </div>


                    <div className="rounded-xl border border-slate-200 bg-white p-3">

                      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        Threshold Ratio
                      </p>


                      <p className="mt-2 text-xl font-semibold text-slate-900">

                        {Number.isFinite(
                          statisticalRatioPercent
                        )
                          ? `${statisticalRatioPercent.toFixed(2)}%`
                          : 'N/A'}

                      </p>

                    </div>

                  </div>


                  {/* SCORE VS THRESHOLD */}

                  {hasStatisticalMetrics && (

                    <div className="px-4 pb-4">

                      <div className="rounded-xl border border-slate-200 bg-white p-4">

                        <div className="flex items-center justify-between gap-4">

                          <div>

                            <p className="text-sm font-semibold text-slate-800">
                              Score vs threshold
                            </p>


                            <p className="mt-1 text-xs text-slate-500">

                              Current score compared with the
                              statistical screening threshold.

                            </p>

                          </div>


                          <span
                            className={`text-sm font-bold ${
                              statisticalOutlier
                                ? 'text-amber-700'
                                : 'text-emerald-700'
                            }`}
                          >

                            {scoreVsThresholdPercent.toFixed(1)}%

                          </span>

                        </div>


                        <div className="mt-4">

                          <div className="h-2.5 overflow-hidden rounded-full bg-slate-200">

                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                statisticalOutlier
                                  ? 'bg-amber-500'
                                  : 'bg-emerald-500'
                              }`}
                              style={{
                                width:
                                  `${safeScoreVsThresholdPercent}%`,
                              }}
                            />

                          </div>


                          <div className="mt-2 flex justify-between text-[11px] text-slate-500">

                            <span>
                              Score: {parsedStatisticalScore.toFixed(4)}
                            </span>


                            <span>
                              Threshold: {parsedStatisticalThreshold.toFixed(4)}
                            </span>

                          </div>

                        </div>

                      </div>

                    </div>

                  )}


                  {/* INTERPRETATION */}

                  <div className="px-4 pb-4">

                    <div className="rounded-xl bg-white/70 p-3">

                      <p className="text-xs font-semibold text-slate-700">
                        Screening interpretation
                      </p>


                      <p className="mt-1 text-xs leading-5 text-slate-600">

                        {outlier.interpretation ||
                          (
                            statisticalOutlier
                              ? 'The anomaly score reached or exceeded the statistical threshold.'
                              : 'The anomaly score remained below the statistical threshold.'
                          )}

                      </p>

                    </div>

                  </div>


                  {/* OUTLIER WARNING */}

                  {statisticalOutlier && (

                    <div className="mx-4 mb-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-100/60 px-3 py-3">

                      <AlertTriangle
                        size={16}
                        className="mt-0.5 shrink-0 text-amber-700"
                      />


                      <div>

                        <p className="text-xs font-semibold text-amber-900">
                          Clinical review recommended
                        </p>


                        <p className="mt-1 text-xs leading-5 text-amber-800">

                          This statistical flag is experimental
                          and does not establish a fetal anomaly
                          or medical diagnosis.

                        </p>

                      </div>

                    </div>

                  )}


                  {/* EXPERIMENTAL DISCLAIMER */}

                  <div className="border-t border-slate-200/70 bg-white/50 px-4 py-3">

                    <p className="text-[11px] leading-5 text-slate-500">

                      <strong className="text-slate-700">
                        Experimental screening:
                      </strong>{' '}

                      Statistical outlier analysis is an
                      experimental model output and is not
                      clinically validated for fetal anomaly
                      diagnosis.

                    </p>

                  </div>

                </div>

              )}


              {/* MODEL 2 NOT PERFORMED */}

              {analysis &&
                analysis.brain_analysis_performed ===
                  false &&
                !outlier && (

                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">

                    <div className="flex items-start gap-2">

                      <Activity
                        size={16}
                        className="mt-0.5 shrink-0 text-slate-400"
                      />


                      <div>

                        <p className="text-sm font-medium text-slate-700">
                          Statistical screening not performed
                        </p>


                        <p className="mt-1 text-xs leading-5 text-slate-500">

                          Brain-plane confidence did not
                          reach the required threshold,
                          so plane-specific statistical
                          screening was skipped.

                        </p>

                      </div>

                    </div>

                  </div>

                )}


              {/* =================================================
                  AI EXPLAINABILITY — GRAD-CAM
              ================================================= */}

              {gradcamAvailable && (

                <div className="rounded-2xl border border-slate-200 bg-white p-4">

                  <div className="flex items-center gap-3">

                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">

                      <Eye size={20} />

                    </div>


                    <div>

                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        AI Explainability
                      </p>


                      <p className="mt-1 font-semibold text-slate-900">
                        Grad-CAM Model Attention
                      </p>

                    </div>

                  </div>


                  <p className="mt-3 text-xs leading-5 text-slate-500">

                    Grad-CAM provides a visual explanation
                    of the image regions that contributed
                    to the fetal-plane classification.

                  </p>


                  <div className="mt-4 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">

                    <span className="text-xs text-slate-500">
                      Target class
                    </span>


                    <span className="text-sm font-semibold text-slate-800">

                      {explainability?.target_class ||
                        fetalPlane?.predicted_class ||
                        'N/A'}

                    </span>

                  </div>


                  <div className="mt-2 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">

                    <span className="text-xs text-slate-500">
                      Model confidence
                    </span>


                    <span className="text-sm font-semibold text-teal-700">

                      {safeExplainabilityConfidence.toFixed(2)}%

                    </span>

                  </div>


                  {explainability?.attention_concentration && (

                    <div className="mt-3 grid grid-cols-2 gap-2">

                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">

                        <p className="text-[11px] text-slate-500">
                          Attention score
                        </p>


                        <p className="mt-1 text-sm font-semibold text-slate-800">

                          {Number(
                            explainability
                              .attention_concentration
                              ?.score ?? 0
                          ).toFixed(4)}

                        </p>

                      </div>


                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">

                        <p className="text-[11px] text-slate-500">
                          Attention status
                        </p>


                        <p className="mt-1 text-sm font-semibold text-slate-800">

                          {explainability
                            .attention_concentration
                            ?.label ||
                            explainability
                              .attention_concentration
                              ?.status ||
                            'N/A'}

                        </p>

                      </div>

                    </div>

                  )}


                  {/* IMAGES */}

                  <div className="mt-4 grid gap-4 sm:grid-cols-2">

                    {/* HEATMAP */}

                    <div className="overflow-hidden rounded-xl border border-slate-200">

                      <div className="border-b border-slate-200 bg-slate-50 px-3 py-2">

                        <p className="text-xs font-semibold text-slate-700">
                          Attention Heatmap
                        </p>

                      </div>


                      <div className="bg-slate-950">

                        {gradcamHeatmapUrl &&
                        !heatmapError ? (

                          <img
                            src={gradcamHeatmapUrl}
                            alt="Grad-CAM attention heatmap"
                            className="h-56 w-full object-contain"
                            loading="lazy"
                            onError={() => {

                              console.error(
                                'Grad-CAM heatmap failed to load:',
                                gradcamHeatmapUrl
                              );

                              setHeatmapError(true);

                            }}
                          />

                        ) : (

                          <div className="flex h-56 items-center justify-center px-4 text-center text-xs text-slate-400">

                            {gradcamHeatmapUrl
                              ? 'Heatmap could not be loaded.'
                              : 'Heatmap unavailable'}

                          </div>

                        )}

                      </div>

                    </div>


                    {/* OVERLAY */}

                    <div className="overflow-hidden rounded-xl border border-slate-200">

                      <div className="border-b border-slate-200 bg-slate-50 px-3 py-2">

                        <p className="text-xs font-semibold text-slate-700">
                          Grad-CAM Overlay
                        </p>

                      </div>


                      <div className="bg-slate-950">

                        {gradcamOverlayUrl &&
                        !overlayError ? (

                          <img
                            src={gradcamOverlayUrl}
                            alt="Grad-CAM overlay"
                            className="h-56 w-full object-contain"
                            loading="lazy"
                            onError={() => {

                              console.error(
                                'Grad-CAM overlay failed to load:',
                                gradcamOverlayUrl
                              );

                              setOverlayError(true);

                            }}
                          />

                        ) : (

                          <div className="flex h-56 items-center justify-center px-4 text-center text-xs text-slate-400">

                            {gradcamOverlayUrl
                              ? 'Grad-CAM overlay could not be loaded.'
                              : 'Overlay unavailable'}

                          </div>

                        )}

                      </div>

                    </div>

                  </div>


                  {/* ATTENTION INTERPRETATION */}

                  {(
                    explainability
                      ?.attention_concentration
                      ?.interpretation
                  ) && (

                    <div className="mt-4 rounded-xl bg-slate-50 px-3 py-3">

                      <p className="text-xs font-medium text-slate-700">
                        Attention interpretation
                      </p>


                      <p className="mt-1 text-xs leading-5 text-slate-500">

                        {
                          explainability
                            .attention_concentration
                            .interpretation
                        }

                      </p>

                    </div>

                  )}


                  {/* CLINICAL NOTE */}

                  <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3">

                    <AlertTriangle
                      size={15}
                      className="mt-0.5 shrink-0 text-amber-700"
                    />


                    <p className="text-xs leading-5 text-amber-800">

                      Grad-CAM is an AI explainability
                      tool. Highlighted regions indicate
                      model attention and should not be
                      interpreted as anatomical
                      segmentation or a clinical diagnosis.

                    </p>

                  </div>

                </div>

              )}


              {/* GRAD-CAM UNAVAILABLE */}

              {result &&
                !gradcamAvailable &&
                fetalPlane && (

                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">

                  <div className="flex items-start gap-2">

                    <Eye
                      size={16}
                      className="mt-0.5 shrink-0 text-slate-400"
                    />


                    <div>

                      <p className="text-sm font-medium text-slate-700">
                        AI explainability unavailable
                      </p>


                      <p className="mt-1 text-xs leading-5 text-slate-500">

                        The ultrasound analysis completed
                        successfully, but a Grad-CAM
                        explanation was not returned for
                        this scan.

                      </p>

                    </div>

                  </div>

                </div>

              )}


              {/* PIPELINE STATUS */}

              {analysis?.pipeline_status && (

                <div className="flex items-center gap-2 rounded-xl bg-slate-100 px-4 py-3 text-xs text-slate-600">

                  <CheckCircle2
                    size={16}
                    className="text-emerald-600"
                  />

                  {analysis.pipeline_status}

                </div>

              )}


              {/* RESULT ID */}

              {(result?.scan_id || result?.scan?.id || result?.id) && (

                <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">

                  <div className="flex items-center justify-between gap-3">

                    <div>

                      <p className="text-xs text-slate-500">
                        Scan ID
                      </p>


                      <p className="mt-1 text-sm font-semibold text-slate-800">

                        #{result.scan_id || result?.scan?.id || result.id}

                      </p>

                    </div>


                    {(result?.scan_id || result?.scan?.id || result?.id) && (

                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          navigate(
                            `/reports?scan=${encodeURIComponent(
                              result.scan_id ||
                              result?.scan?.id ||
                              result.id
                            )}`
                          )
                        }
                      >

                        <Eye
                          size={16}
                          className="mr-2"
                        />

                        Open Full Report

                      </Button>

                    )}

                  </div>

                </div>

              )}


              {/* DISCLAIMER */}

              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-500">

                <strong className="text-slate-700">
                  Clinical note:
                </strong>{' '}

                AI analysis is intended to assist
                clinical review and should not be used
                as a standalone medical diagnosis.

              </div>


              {/* NEW ANALYSIS */}

              <Button
                type="button"
                variant="secondary"
                onClick={() => {

                  setResult(null);
                  setProgress(0);
                  setError('');

                  setHeatmapError(false);
                  setOverlayError(false);

                }}
                className="w-full"
              >

                <RefreshCw
                  size={17}
                  className="mr-2"
                />

                Analyze another image

              </Button>

            </div>

          )}

        </Card>

      </div>

    </div>

  );
}


export default NewScanPage;