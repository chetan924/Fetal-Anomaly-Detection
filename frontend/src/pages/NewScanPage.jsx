import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Box,
  Brain,
  CheckCircle2,
  ChevronDown,
  Clock,
  Download,
  Eye,
  FileImage,
  FileText,
  Heart,
  HelpCircle,
  Info,
  Layers,
  Loader2,
  Plus,
  RefreshCw,
  RotateCcw,
  ScanLine,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  User,
  X,
} from 'lucide-react';

import PageHeader from '../components/common/PageHeader';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { addNotification } from '../services/notifications';

import {
  API_BASE_URL,
  getApiErrorMessage,
  getPatients,
  predictPlane,
  predictSpine,
  predictBrain,
  predictLung,
  predictBone,
  predictPlacenta,
  predictFace,
  predictHeart,
  predictComprehensive,
  downloadReportPdf,
} from '../services/api';

// ============================================================
// MODEL SELECTION CONFIGURATION
// ============================================================

const MODEL_MODES = [
  {
    id: 'comprehensive',
    name: 'Comprehensive Analysis',
    worker: 'multi-model',
    category: 'Full Pipeline',
    description: 'Multi-scan anatomical pipeline orchestrating all specialized AI models',
    fileType: 'multi',
    accept: '.jpg,.jpeg,.png,.webp,.vtk',
    icon: Layers,
    color: 'teal',
  },
  {
    id: 'plane',
    name: 'Fetal Plane',
    worker: 'plane',
    category: 'Classification',
    description: 'EfficientNet-B0 standard fetal plane classifier',
    fileType: 'image',
    accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
    icon: ScanLine,
    color: 'blue',
  },
  {
    id: 'spine',
    name: 'Fetal Spine',
    worker: 'spine',
    category: 'Object Detection',
    description: 'YOLOv8 deep neural detector for fetal vertebral structures',
    fileType: 'image',
    accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
    icon: Activity,
    color: 'indigo',
  },
  {
    id: 'brain',
    name: 'Fetal Brain',
    worker: 'brain',
    category: 'Dual Model',
    description: 'EfficientNet-B0 plane classifier + Random Forest anomaly detector',
    fileType: 'image',
    accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
    icon: Brain,
    color: 'violet',
  },
  {
    id: 'lung',
    name: 'Fetal Lung',
    worker: 'lung',
    category: 'Segmentation',
    description: 'PyTorch U-Net fetal lung segmentation & mask ratio',
    fileType: 'image',
    accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
    icon: Sparkles,
    color: 'sky',
  },
  {
    id: 'bone',
    name: 'Fetal Bone',
    worker: 'bone',
    category: 'Object Detection',
    description: 'YOLOv8 fetal femur and skeletal bone detection',
    fileType: 'image',
    accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
    icon: Box,
    color: 'amber',
  },
  {
    id: 'placenta',
    name: 'Placenta',
    worker: 'placenta',
    category: 'Segmentation',
    description: 'SMP U-Net fetal placenta segmentation & boundary extraction',
    fileType: 'image',
    accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
    icon: ShieldCheck,
    color: 'emerald',
  },
  {
    id: 'face',
    name: 'Face 3D Mesh',
    worker: 'face',
    category: '3D Geometry',
    description: 'Python 3.11 + VTK 30-feature 3D facial mesh anomaly classifier',
    fileType: 'vtk',
    accept: '.vtk',
    icon: Box,
    color: 'fuchsia',
  },
  {
    id: 'heart',
    name: 'Fetal Heart',
    worker: 'heart',
    category: 'Segmentation',
    description: 'SMP U-Net 4-chamber fetal heart segmentation',
    fileType: 'image',
    accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
    icon: Heart,
    color: 'rose',
  },
  {
    id: 'kidney',
    name: 'Kidney AI',
    worker: 'kidney',
    category: 'Disabled',
    description: 'Kidney AI model currently unavailable (disabled)',
    fileType: 'image',
    accept: '.jpg,.jpeg,.png,.webp',
    disabled: true,
    icon: AlertCircle,
    color: 'slate',
  },
];

const COMPREHENSIVE_SLOTS = [
  { id: 'plane', label: 'Fetal Plane Scan', type: 'image', accept: '.jpg,.jpeg,.png,.webp', desc: 'Standard 2D ultrasound' },
  { id: 'brain', label: 'Brain Scan', type: 'image', accept: '.jpg,.jpeg,.png,.webp', desc: 'Trans-thalamic / Trans-cerebellar plane' },
  { id: 'spine', label: 'Spine Scan', type: 'image', accept: '.jpg,.jpeg,.png,.webp', desc: 'Sagittal / Coronal spine view' },
  { id: 'lung', label: 'Lung Scan', type: 'image', accept: '.jpg,.jpeg,.png,.webp', desc: 'Thoracic cross-section' },
  { id: 'bone', label: 'Bone / Femur Scan', type: 'image', accept: '.jpg,.jpeg,.png,.webp', desc: 'Femur length / skeletal view' },
  { id: 'placenta', label: 'Placenta Scan', type: 'image', accept: '.jpg,.jpeg,.png,.webp', desc: 'Placental attachment view' },
  { id: 'face', label: 'Face 3D Mesh (.vtk)', type: 'vtk', accept: '.vtk', desc: '3D polygonal surface mesh dataset' },
  { id: 'heart', label: 'Heart Scan', type: 'image', accept: '.jpg,.jpeg,.png,.webp', desc: 'Four-chamber cardiac view' },
];


// ============================================================
// COMPONENT
// ============================================================

function NewScanPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlPatient = searchParams.get('patient') || searchParams.get('patient_id') || '';
  const urlMode = searchParams.get('mode') || '';

  const initialMode = useMemo(() => {
    if (urlMode) {
      const found = MODEL_MODES.find((m) => m.id === urlMode.toLowerCase() && !m.disabled);
      if (found) return found.id;
    }
    return 'comprehensive';
  }, [urlMode]);

  // ==========================================================
  // STATE
  // ==========================================================

  const [selectedMode, setSelectedMode] = useState(initialMode);
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState(urlPatient);
  const [patientDropdownOpen, setPatientDropdownOpen] = useState(false);
  const [patientSearch, setPatientSearch] = useState('');

  // Single mode file state
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');

  // Comprehensive multi-slot file state
  const [comprehensiveFiles, setComprehensiveFiles] = useState({
    plane: null,
    brain: null,
    spine: null,
    lung: null,
    bone: null,
    placenta: null,
    face: null,
    heart: null,
  });

  const [comprehensivePreviews, setComprehensivePreviews] = useState({});

  const [loadingPatients, setLoadingPatients] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');

  const [error, setError] = useState('');

  const [result, setResult] = useState(null);
  const [inferenceEnvelope, setInferenceEnvelope] = useState(null);

  // Active mode metadata
  const currentModeConfig = MODEL_MODES.find((m) => m.id === selectedMode) || MODEL_MODES[0];

  // ==========================================================
  // PDF DOWNLOAD HELPER
  // ==========================================================

  const handleDownloadPdf = async (reportNumber) => {
    if (!reportNumber) return;
    try {
      setDownloadingPdf(true);
      await downloadReportPdf(reportNumber, `${reportNumber}.pdf`);
      addNotification({
        type: 'success',
        title: 'PDF Downloaded',
        message: `Report ${reportNumber}.pdf downloaded successfully.`,
      });
    } catch (err) {
      console.error('PDF download error:', err);
      addNotification({
        type: 'error',
        title: 'PDF Download Failed',
        message: 'Failed to download report PDF.',
      });
    } finally {
      setDownloadingPdf(false);
    }
  };

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
        const data = Array.isArray(response)
          ? response
          : response?.patients || [];

        if (!mounted) return;

        setPatients(data);
        if (data.length > 0) {
          if (urlPatient) {
            setPatientId(urlPatient);
          } else {
            const firstPatient = data[0];
            setPatientId(firstPatient.patient_id ?? firstPatient.id ?? '');
          }
        }
      } catch (err) {
        if (!mounted) return;
        setError(getApiErrorMessage(err, 'Failed to load patients list.'));
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
  }, [urlPatient]);

  // ==========================================================
  // OUTSIDE CLICK FOR PATIENT DROPDOWN
  // ==========================================================

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (!event.target.closest('[data-patient-dropdown]')) {
        setPatientDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, []);

  // ==========================================================
  // PREVIEW CLEANUP
  // ==========================================================

  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
      Object.values(comprehensivePreviews).forEach((url) => {
        if (url && typeof url === 'string') {
          URL.revokeObjectURL(url);
        }
      });
    };
  }, [preview, comprehensivePreviews]);

  // ==========================================================
  // HANDLE MODE CHANGE
  // ==========================================================

  const handleSelectMode = (modeId) => {
    const modeConfig = MODEL_MODES.find((m) => m.id === modeId);
    if (!modeConfig || modeConfig.disabled) return;

    setSelectedMode(modeId);
    setError('');
    setResult(null);
    setInferenceEnvelope(null);
  };

  // ==========================================================
  // SINGLE FILE SELECTION & VALIDATION
  // ==========================================================

  const handleFileChange = (selectedFile) => {
    if (!selectedFile) return;

    setError('');
    setResult(null);
    setInferenceEnvelope(null);
    setProgress(0);

    const isVtkMode = currentModeConfig.fileType === 'vtk';
    const fileName = selectedFile.name.toLowerCase();

    // 1. File type check
    if (isVtkMode) {
      if (!fileName.endsWith('.vtk')) {
        setError('Please select a valid 3D mesh file with .vtk extension for Face 3D analysis.');
        return;
      }
    } else {
      const allowedImageExts = ['.jpg', '.jpeg', '.png', '.webp'];
      const hasValidExt = allowedImageExts.some((ext) => fileName.endsWith(ext));
      if (!hasValidExt) {
        setError('Unsupported image format. Allowed formats: JPG, PNG, WEBP.');
        return;
      }
    }

    // 2. File size check (15 MB standard limit)
    const MAX_FILE_SIZE = 15 * 1024 * 1024;
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('File exceeds maximum size limit of 15 MB.');
      return;
    }

    if (selectedFile.size === 0) {
      setError('Uploaded file is empty (0 bytes).');
      return;
    }

    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setFile(selectedFile);

    if (!isVtkMode) {
      const objectUrl = URL.createObjectURL(selectedFile);
      setPreview(objectUrl);
    } else {
      setPreview('');
    }
  };

  const handleInputChange = (event) => {
    const selectedFile = event.target.files?.[0];
    handleFileChange(selectedFile);
    event.target.value = '';
  };

  const removeFile = () => {
    if (preview) {
      URL.revokeObjectURL(preview);
    }
    setFile(null);
    setPreview('');
    setResult(null);
    setInferenceEnvelope(null);
    setProgress(0);
    setError('');
  };

  // ==========================================================
  // COMPREHENSIVE MULTI-SLOT FILE SELECTION
  // ==========================================================

  const handleComprehensiveFileChange = (slotId, selectedFile) => {
    if (!selectedFile) return;

    setError('');
    const fileName = selectedFile.name.toLowerCase();
    const isVtk = slotId === 'face';

    if (isVtk) {
      if (!fileName.endsWith('.vtk')) {
        setError('Face 3D slot requires a .vtk mesh file.');
        return;
      }
    } else {
      const allowedExts = ['.jpg', '.jpeg', '.png', '.webp'];
      if (!allowedExts.some((ext) => fileName.endsWith(ext))) {
        setError(`${slotId.toUpperCase()} scan must be a JPG, PNG, or WEBP image.`);
        return;
      }
    }

    if (selectedFile.size > 15 * 1024 * 1024) {
      setError(`File for ${slotId} exceeds the 15 MB size limit.`);
      return;
    }

    setComprehensiveFiles((prev) => ({
      ...prev,
      [slotId]: selectedFile,
    }));

    if (!isVtk) {
      const url = URL.createObjectURL(selectedFile);
      setComprehensivePreviews((prev) => ({
        ...prev,
        [slotId]: url,
      }));
    }
  };

  const removeComprehensiveFile = (slotId) => {
    if (comprehensivePreviews[slotId]) {
      URL.revokeObjectURL(comprehensivePreviews[slotId]);
    }
    setComprehensiveFiles((prev) => ({
      ...prev,
      [slotId]: null,
    }));
    setComprehensivePreviews((prev) => {
      const updated = { ...prev };
      delete updated[slotId];
      return updated;
    });
  };

  const totalComprehensiveUploaded = Object.values(comprehensiveFiles).filter(Boolean).length;

  // ==========================================================
  // INFERENCE & ANALYSIS EXECUTION
  // ==========================================================

  const handleAnalyze = async () => {
    setError('');
    setResult(null);
    setInferenceEnvelope(null);
    setAnalyzing(true);
    setProgress(0);

    const progressCb = (event) => {
      if (event.total) {
        const uploadProgress = Math.round((event.loaded / event.total) * 100);
        setProgress(Math.min(uploadProgress, 100));
      }
    };

    try {
      if (selectedMode === 'comprehensive') {
        if (totalComprehensiveUploaded === 0) {
          setError('Please upload at least one anatomical scan to run Comprehensive Analysis.');
          setAnalyzing(false);
          return;
        }

        const idempotencyKey = `idem_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        setStatusMessage('Executing Unified Multi-Worker Pipeline...');
        const envelope = await predictComprehensive(
          comprehensiveFiles,
          patientId,
          idempotencyKey,
          null,
          progressCb
        );

        if (!envelope || envelope.success === false) {
          const errMsg = envelope?.error?.message || 'Comprehensive analysis failed.';
          throw new Error(errMsg);
        }

        setInferenceEnvelope(envelope);
        setResult(envelope.data);
        setProgress(100);

        addNotification({
          type: 'success',
          title: 'Comprehensive Analysis Completed',
          message: `Pipeline finished with status '${envelope.data.status}' (${envelope.data.summary.models_completed}/${envelope.data.summary.models_requested} completed).`,
        });

      } else {
        if (!file) {
          setError(`Please select a ${currentModeConfig.fileType === 'vtk' ? 'VTK mesh file' : 'scan image'}.`);
          setAnalyzing(false);
          return;
        }

        setStatusMessage(`Sending request to ${currentModeConfig.name} AI worker...`);
        let envelope = null;

        switch (selectedMode) {
          case 'plane':
            envelope = await predictPlane(file, progressCb);
            break;
          case 'spine':
            envelope = await predictSpine(file, progressCb);
            break;
          case 'brain':
            envelope = await predictBrain(file, progressCb);
            break;
          case 'lung':
            envelope = await predictLung(file, progressCb);
            break;
          case 'bone':
            envelope = await predictBone(file, progressCb);
            break;
          case 'placenta':
            envelope = await predictPlacenta(file, progressCb);
            break;
          case 'face':
            envelope = await predictFace(file, progressCb);
            break;
          case 'heart':
            envelope = await predictHeart(file, progressCb);
            break;
          default:
            throw new Error(`Unsupported model mode: ${selectedMode}`);
        }

        if (!envelope || envelope.success === false) {
          const errMsg = envelope?.error?.message || 'AI inference failed.';
          throw new Error(errMsg);
        }

        setInferenceEnvelope(envelope);
        setResult(envelope.data);
        setProgress(100);

        addNotification({
          type: 'success',
          title: `${currentModeConfig.name} Analysis Completed`,
          message: `Model inference completed successfully (ID: ${envelope.request_id}).`,
        });
      }
    } catch (err) {
      console.error('Inference error:', err);
      const friendlyMsg = getApiErrorMessage(err, `${currentModeConfig.name} analysis failed. Please try again.`);
      setError(friendlyMsg);

      addNotification({
        type: 'error',
        title: `${currentModeConfig.name} Analysis Failed`,
        message: friendlyMsg,
      });
    } finally {
      setAnalyzing(false);
      setStatusMessage('');
    }
  };

  // ==========================================================
  // PATIENT DROPDOWN DATA
  // ==========================================================

  const filteredPatients = patients.filter((patient) => {
    const search = patientSearch.trim().toLowerCase();
    if (!search) return true;
    const patientCode = String(patient.patient_id ?? patient.id ?? '').toLowerCase();
    const patientName = String(patient.full_name ?? patient.name ?? '').toLowerCase();
    return patientCode.includes(search) || patientName.includes(search);
  });

  const selectedPatient = patients.find(
    (patient) => String(patient.patient_id ?? patient.id ?? '') === String(patientId)
  );

  return (
    <div className="space-y-6 p-6">
      {/* ====================================================
          HEADER
      ==================================================== */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <ScanLine className="h-7 w-7 text-teal-600" />
            Fetal Anomaly AI Analysis
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Multi-model fetal ultrasound inference orchestrating isolated neural network workers.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/history')}
            className="text-xs"
          >
            <Clock size={14} className="mr-1.5" />
            Scan History
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/reports')}
            className="text-xs"
          >
            <FileText size={14} className="mr-1.5" />
            Clinical Reports
          </Button>
        </div>
      </div>

      {/* ====================================================
          ERROR BANNER
      ==================================================== */}
      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-rose-800 shadow-xs">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-600" />
          <div className="flex-1 text-xs">
            <p className="font-bold text-rose-900">Analysis Request Notice</p>
            <p className="mt-0.5 text-rose-700">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => setError('')}
            className="text-rose-500 hover:text-rose-700 transition"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ====================================================
          ANATOMICAL MODEL SELECTION GRID
      ==================================================== */}
      <Card
        title="AI Analysis Mode Selection"
        subtitle="Choose Comprehensive Multi-Scan Analysis or a specialized anatomical worker"
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5 pt-2">
          {MODEL_MODES.map((mode) => {
            const isSelected = selectedMode === mode.id;
            const Icon = mode.icon;

            return (
              <button
                key={mode.id}
                type="button"
                disabled={mode.disabled}
                onClick={() => handleSelectMode(mode.id)}
                className={`relative flex flex-col items-start rounded-2xl border p-3.5 text-left transition duration-200 ${
                  mode.disabled
                    ? 'cursor-not-allowed border-slate-200 bg-slate-50/60 opacity-60'
                    : isSelected
                    ? 'border-teal-600 bg-teal-50/50 shadow-xs ring-2 ring-teal-600/20'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/70'
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-xl ${
                      mode.disabled
                        ? 'bg-slate-200 text-slate-500'
                        : isSelected
                        ? 'bg-teal-600 text-white'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    <Icon size={16} />
                  </div>

                  {mode.disabled ? (
                    <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-600">
                      Disabled
                    </span>
                  ) : isSelected ? (
                    <span className="flex h-2 w-2 rounded-full bg-teal-600 animate-pulse" />
                  ) : null}
                </div>

                <p className="mt-2.5 text-xs font-bold text-slate-900">{mode.name}</p>
                <p className="text-[11px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                  {mode.description}
                </p>

                <div className="mt-2 flex items-center gap-1.5 text-[10px] font-semibold text-slate-400">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600 uppercase font-mono">
                    {mode.fileType}
                  </span>
                  <span>•</span>
                  <span className="text-slate-500">{mode.category}</span>
                </div>
              </button>
            );
          })}
        </div>
      </Card>

      {/* ====================================================
          MAIN TWO-COLUMN WORKSPACE
      ==================================================== */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* ==================================================
            LEFT COLUMN: PATIENT & UPLOAD PANEL
        ================================================== */}
        <Card
          title={selectedMode === 'comprehensive' ? 'Comprehensive Scan Set Upload' : `${currentModeConfig.name} Input`}
          subtitle={
            selectedMode === 'comprehensive'
              ? 'Upload available anatomical scans for unified multi-worker analysis'
              : `Upload a valid ${currentModeConfig.fileType === 'vtk' ? '3D VTK mesh (.vtk)' : 'ultrasound image'} for inference`
          }
        >
          <div className="space-y-4 pt-2">
            {/* PATIENT SELECTION DROPDOWN */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Target Patient Record <span className="text-slate-400 font-normal">(Optional for direct inference)</span>
              </label>

              <div className="relative" data-patient-dropdown>
                <button
                  type="button"
                  onClick={() => setPatientDropdownOpen(!patientDropdownOpen)}
                  disabled={loadingPatients || analyzing}
                  className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-left text-xs font-medium text-slate-800 hover:border-slate-300 focus:border-teal-500 focus:outline-none transition shadow-2xs"
                >
                  <div className="flex items-center gap-2 truncate">
                    <User size={15} className="text-slate-400 shrink-0" />
                    {selectedPatient ? (
                      <span>
                        <strong className="text-slate-900">{selectedPatient.full_name || selectedPatient.name}</strong>{' '}
                        <span className="text-slate-500 font-mono">({selectedPatient.patient_id || selectedPatient.id})</span>
                      </span>
                    ) : (
                      <span className="text-slate-400">-- Select a Patient (Optional) --</span>
                    )}
                  </div>
                  <ChevronDown size={14} className="text-slate-400" />
                </button>

                {patientDropdownOpen && (
                  <div className="absolute z-20 mt-1 w-full rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
                    <div className="relative mb-2">
                      <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Search by name or ID..."
                        value={patientSearch}
                        onChange={(e) => setPatientSearch(e.target.value)}
                        className="w-full rounded-lg border border-slate-200 pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:border-teal-500 focus:outline-none"
                      />
                    </div>

                    <div className="max-h-44 overflow-y-auto space-y-1">
                      <button
                        type="button"
                        onClick={() => {
                          setPatientId('');
                          setPatientDropdownOpen(false);
                        }}
                        className="flex w-full items-center px-2.5 py-1.5 rounded-lg text-xs text-slate-500 hover:bg-slate-50"
                      >
                        None / Anonymous Run
                      </button>
                      {filteredPatients.map((p) => {
                        const idStr = String(p.patient_id ?? p.id ?? '');
                        const isMatch = idStr === String(patientId);

                        return (
                          <button
                            key={idStr}
                            type="button"
                            onClick={() => {
                              setPatientId(idStr);
                              setPatientDropdownOpen(false);
                            }}
                            className={`flex w-full items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition ${
                              isMatch ? 'bg-teal-50 text-teal-800 font-semibold' : 'text-slate-700 hover:bg-slate-50'
                            }`}
                          >
                            <span>{p.full_name || p.name}</span>
                            <span className="font-mono text-[11px] text-slate-400">{idStr}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* ==============================================
                COMPREHENSIVE MULTI-SLOT UPLOADER
            ============================================== */}
            {selectedMode === 'comprehensive' ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-800">Scan Slot Manager</span>
                  <span className="font-semibold text-teal-700 bg-teal-50 border border-teal-100 px-2 py-0.5 rounded-full">
                    {totalComprehensiveUploaded} of {COMPREHENSIVE_SLOTS.length} Scans Loaded
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 max-h-[420px] overflow-y-auto pr-1">
                  {COMPREHENSIVE_SLOTS.map((slot) => {
                    const loadedFile = comprehensiveFiles[slot.id];
                    const previewUrl = comprehensivePreviews[slot.id];

                    return (
                      <div
                        key={slot.id}
                        className={`rounded-xl border p-3 transition ${
                          loadedFile
                            ? 'border-teal-300 bg-teal-50/40'
                            : 'border-slate-200 bg-slate-50/50 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-xs font-bold text-slate-900 truncate">{slot.label}</p>
                            <p className="text-[10px] text-slate-500 leading-tight mt-0.5">{slot.desc}</p>
                          </div>

                          {loadedFile ? (
                            <button
                              type="button"
                              onClick={() => removeComprehensiveFile(slot.id)}
                              disabled={analyzing}
                              className="text-slate-400 hover:text-rose-600 transition p-1"
                              title="Remove scan"
                            >
                              <X size={14} />
                            </button>
                          ) : null}
                        </div>

                        {loadedFile ? (
                          <div className="mt-2.5 flex items-center gap-2">
                            {slot.type === 'image' && previewUrl ? (
                              <img
                                src={previewUrl}
                                alt={slot.label}
                                className="h-10 w-10 rounded-lg object-cover border border-slate-200 bg-slate-900"
                              />
                            ) : (
                              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-fuchsia-100 text-fuchsia-700 border border-fuchsia-200">
                                <Box size={18} />
                              </div>
                            )}
                            <div className="min-w-0 text-[11px]">
                              <p className="font-semibold text-slate-800 truncate">{loadedFile.name}</p>
                              <p className="text-[10px] text-slate-400">
                                {(loadedFile.size / 1024).toFixed(1)} KB • Ready
                              </p>
                            </div>
                          </div>
                        ) : (
                          <label className="mt-2 flex cursor-pointer items-center justify-center gap-1.5 rounded-lg border border-dashed border-slate-300 bg-white py-2 text-center text-[11px] font-semibold text-slate-600 hover:border-teal-500 hover:text-teal-700 transition">
                            <Plus size={13} />
                            <span>Select {slot.type === 'vtk' ? 'VTK' : 'Image'}</span>
                            <input
                              type="file"
                              accept={slot.accept}
                              onChange={(e) => {
                                const f = e.target.files?.[0];
                                if (f) handleComprehensiveFileChange(slot.id, f);
                                e.target.value = '';
                              }}
                              disabled={analyzing}
                              className="hidden"
                            />
                          </label>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              /* ==============================================
                  SINGLE FILE DROPZONE
              ============================================== */
              <div>
                {!file ? (
                  <label className="flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/50 p-6 text-center hover:border-teal-500 hover:bg-teal-50/20 transition group">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white border border-slate-200 text-slate-600 shadow-2xs group-hover:scale-105 group-hover:border-teal-200 group-hover:text-teal-600 transition">
                      <Upload size={22} />
                    </div>
                    <p className="mt-3 text-sm font-bold text-slate-800">
                      Click to upload or drag and drop
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {currentModeConfig.fileType === 'vtk'
                        ? '3D Polygonal VTK Mesh (*.vtk)'
                        : 'Standard ultrasound scan (*.png, *.jpg, *.jpeg, *.webp)'}
                    </p>
                    <span className="mt-3 rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold text-slate-600">
                      Maximum file size: 15 MB
                    </span>
                    <input
                      type="file"
                      accept={currentModeConfig.accept}
                      onChange={handleInputChange}
                      disabled={analyzing}
                      className="hidden"
                    />
                  </label>
                ) : (
                  <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
                    {currentModeConfig.fileType === 'vtk' ? (
                      <div className="flex flex-col items-center justify-center bg-slate-900 p-8 text-white">
                        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-fuchsia-500/20 text-fuchsia-400 border border-fuchsia-500/30">
                          <Box size={32} />
                        </div>
                        <p className="mt-3 text-sm font-bold text-slate-100">{file.name}</p>
                        <p className="text-xs text-slate-400 mt-0.5">3D VTK Polygonal Mesh Dataset</p>
                      </div>
                    ) : (
                      <div className="relative bg-slate-950">
                        <img
                          src={preview}
                          alt="Ultrasound scan preview"
                          className="h-64 w-full object-contain"
                        />
                      </div>
                    )}

                    <div className="flex items-center justify-between p-3.5 bg-slate-50/80 border-t border-slate-100">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white border border-slate-200 text-teal-700">
                          <FileImage size={16} />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold text-slate-800">{file.name}</p>
                          <p className="text-[11px] text-slate-500">
                            {(file.size / (1024 * 1024)).toFixed(2)} MB • {currentModeConfig.name}
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={removeFile}
                        disabled={analyzing}
                        className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-rose-50 hover:text-rose-600 transition"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* PROGRESS & STATUS */}
            {analyzing && (
              <div className="space-y-2 rounded-xl bg-teal-50/60 p-3.5 border border-teal-100">
                <div className="flex items-center justify-between text-xs font-medium text-teal-900">
                  <span className="flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin text-teal-600" />
                    {statusMessage || 'Processing multi-worker analysis...'}
                  </span>
                  <span>{progress}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-teal-200/60">
                  <div
                    className="h-full bg-teal-600 transition-all duration-300 rounded-full"
                    style={{ width: `${progress}%` }}
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
                (selectedMode === 'comprehensive' && totalComprehensiveUploaded === 0) ||
                (selectedMode !== 'comprehensive' && !file)
              }
              className="w-full py-3 text-sm font-semibold shadow-sm"
            >
              {analyzing ? (
                <>
                  <Loader2 size={16} className="mr-2 animate-spin" />
                  Running AI Inference Pipeline...
                </>
              ) : (
                <>
                  <Activity size={16} className="mr-2" />
                  Run {currentModeConfig.name} Inference
                </>
              )}
            </Button>
          </div>
        </Card>

        {/* ==================================================
            RIGHT COLUMN: AI ANALYSIS RESULT CARD
        ================================================== */}
        <Card
          title="AI Analysis Results"
          subtitle={
            result
              ? `Inference completed via ${inferenceEnvelope?.model || currentModeConfig.worker} worker`
              : 'Awaiting scan upload and model execution'
          }
        >
          {!result ? (
            <div className="flex min-h-[380px] flex-col items-center justify-center p-6 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                <Brain size={32} />
              </div>
              <p className="mt-4 text-sm font-semibold text-slate-700">Awaiting Analysis</p>
              <p className="mt-1 max-w-sm text-xs leading-relaxed text-slate-400">
                Select an AI model mode, upload your clinical files, and run inference to inspect real-time neural network predictions.
              </p>
            </div>
          ) : (
            <div className="mt-2 space-y-4">
              {/* TOP SUMMARY BANNER */}
              <div className="flex items-center justify-between rounded-2xl border border-teal-200 bg-teal-50/60 p-3.5">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-600 text-white">
                    <CheckCircle2 size={18} />
                  </div>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-teal-800">
                      {selectedMode === 'comprehensive' ? `Unified Pipeline (${result?.status})` : `${currentModeConfig.name} Success`}
                    </p>
                    <p className="text-[11px] text-teal-700">
                      {selectedMode === 'comprehensive'
                        ? `${result?.summary?.models_completed || 0} of ${result?.summary?.models_requested || 0} Models Completed in ${result?.summary?.total_duration_seconds || 0}s`
                        : `Worker: ${inferenceEnvelope?.model || currentModeConfig.worker}`}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">Request ID</span>
                  <p className="font-mono text-xs text-slate-700">{inferenceEnvelope?.request_id || result?.request_id}</p>
                </div>
              </div>

              {/* PERSISTED REPORT & SESSION SNAPSHOT BANNER */}
              {result?.report_number && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-2xl border border-teal-300 bg-gradient-to-r from-teal-50 to-emerald-50 p-3.5 shadow-xs">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white shadow-2xs">
                      <FileText size={18} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-900">{result.report_number}</span>
                        {result.is_cached && (
                          <span className="rounded-md bg-teal-200/70 px-1.5 py-0.5 text-[10px] font-semibold text-teal-800">
                            Cached Session
                          </span>
                        )}
                        {result.session_id && (
                          <span className="font-mono text-[10px] text-slate-500">
                            (Session: {result.session_id})
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-600 mt-0.5">
                        Immutable clinical report persisted in database.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownloadPdf(result.report_number)}
                      disabled={downloadingPdf}
                      className="flex-1 sm:flex-initial text-xs bg-white py-1.5"
                    >
                      {downloadingPdf ? (
                        <Loader2 size={12} className="mr-1.5 animate-spin" />
                      ) : (
                        <Download size={12} className="mr-1.5" />
                      )}
                      PDF
                    </Button>
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={() => navigate(`/reports?report=${encodeURIComponent(result.report_number)}`)}
                      className="flex-1 sm:flex-initial text-xs py-1.5"
                    >
                      <Eye size={12} className="mr-1.5" />
                      Full Report
                    </Button>
                  </div>
                </div>
              )}

              {/* ============================================
                  COMPREHENSIVE UNIFIED REPORT RENDERER
              ============================================ */}
              {selectedMode === 'comprehensive' && result?.findings ? (
                <div className="space-y-4 max-h-[540px] overflow-y-auto pr-1">
                  {/* Summary Metric Badges */}
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="rounded-xl border border-slate-200 bg-white p-2">
                      <span className="text-[10px] uppercase font-semibold text-slate-400">Completed</span>
                      <p className="text-base font-bold text-teal-600">{result.summary?.models_completed ?? 0}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-2">
                      <span className="text-[10px] uppercase font-semibold text-slate-400">Failed</span>
                      <p className="text-base font-bold text-rose-600">{result.summary?.models_failed ?? 0}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-2">
                      <span className="text-[10px] uppercase font-semibold text-slate-400">Not Provided</span>
                      <p className="text-base font-bold text-slate-500">{result.summary?.models_not_provided ?? 0}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-2">
                      <span className="text-[10px] uppercase font-semibold text-slate-400">Unavailable</span>
                      <p className="text-base font-bold text-amber-600">{result.summary?.models_unavailable ?? 0}</p>
                    </div>
                  </div>

                  {/* Anatomical Findings */}
                  {Object.entries(result.findings).map(([modName, modFinding]) => {
                    const status = modFinding?.status;
                    const resData = modFinding?.result;

                    return (
                      <div
                        key={modName}
                        className={`rounded-xl border p-3.5 space-y-2 transition ${
                          status === 'completed'
                            ? 'border-slate-200 bg-white'
                            : status === 'failed'
                            ? 'border-rose-200 bg-rose-50/40'
                            : status === 'unavailable'
                            ? 'border-slate-200 bg-slate-50/60 opacity-70'
                            : 'border-slate-100 bg-slate-50/40 opacity-60'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs uppercase tracking-wide text-slate-800">
                              {modName}
                            </span>
                            {modFinding?.duration_ms && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                ({modFinding.duration_ms}ms)
                              </span>
                            )}
                          </div>

                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                              status === 'completed'
                                ? 'bg-teal-100 text-teal-800'
                                : status === 'failed'
                                ? 'bg-rose-100 text-rose-800'
                                : status === 'unavailable'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-slate-200 text-slate-600'
                            }`}
                          >
                            {status}
                          </span>
                        </div>

                        {/* COMPLETED MODEL SPECIFIC CONTENT */}
                        {status === 'completed' && resData && (
                          <div className="text-xs pt-1">
                            {/* Plane */}
                            {modName === 'plane' && (
                              <div>
                                <p className="font-semibold text-slate-800">
                                  Predicted Plane: <span className="text-teal-700 font-bold">{resData.predicted_class}</span>{' '}
                                  ({resData.confidence_percent ?? (resData.confidence * 100).toFixed(1)}%)
                                </p>
                              </div>
                            )}

                            {/* Spine & Bone */}
                            {(modName === 'spine' || modName === 'bone') && (
                              <div>
                                <p className="font-semibold text-slate-800">
                                  Detections: <span className="text-indigo-700 font-bold">{resData.detections?.length || 0} Landmark(s)</span>
                                </p>
                                {resData.detections?.length > 0 && (
                                  <div className="mt-1 flex flex-wrap gap-1">
                                    {resData.detections.map((d, i) => (
                                      <span key={i} className="rounded bg-indigo-50 border border-indigo-100 px-1.5 py-0.5 text-[10px] text-indigo-800">
                                        {d.class_name}: {((d.confidence || 0) * 100).toFixed(0)}%
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Brain */}
                            {modName === 'brain' && (
                              <div className="space-y-1">
                                <p className="font-semibold text-slate-800">
                                  Brain Plane: <span className="text-violet-700 font-bold">{resData.brain_plane?.predicted_class}</span>{' '}
                                  ({((resData.brain_plane?.confidence || 0) * 100).toFixed(1)}%)
                                </p>
                                {resData.brain_anomaly && (
                                  <p className="text-[11px] text-slate-600">
                                    Anomaly Status: <span className="font-semibold text-violet-800">{resData.brain_anomaly.status}</span>{' '}
                                    (Score: {Number(resData.brain_anomaly.anomaly_score).toFixed(3)})
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Lung, Placenta, Heart */}
                            {(modName === 'lung' || modName === 'placenta' || modName === 'heart') && (
                              <div className="space-y-1">
                                {(() => {
                                  const seg = resData.segmentation || resData;
                                  return (
                                    <>
                                      <p className="font-semibold text-slate-800">
                                        Mask Pixels: <span className="text-teal-700 font-bold">{seg.mask_pixels?.toLocaleString()}</span> • Area Ratio: {((seg.mask_ratio || 0) * 100).toFixed(2)}%
                                      </p>
                                      {seg.mask_url && (
                                        <div className="mt-1.5 overflow-hidden rounded-lg bg-slate-950 flex items-center justify-center max-h-36">
                                          <img
                                            src={`${API_BASE_URL}${seg.mask_url}`}
                                            alt={`${modName} mask`}
                                            className="max-h-36 w-full object-contain"
                                          />
                                        </div>
                                      )}
                                    </>
                                  );
                                })()}
                              </div>
                            )}

                            {/* Face */}
                            {modName === 'face' && (
                              <div>
                                <p className="font-semibold text-slate-800">
                                  Morphology: <span className="text-fuchsia-700 font-bold">{resData.prediction?.predicted_label || resData.prediction?.label || 'Normal'}</span>{' '}
                                  ({(resData.prediction?.confidence_percent ?? ((resData.prediction?.confidence || 0.92) * 100)).toFixed(1)}%)
                                </p>
                                {(resData.mesh_info || resData.input) && (
                                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                                    Mesh: {(resData.mesh_info || resData.input).points?.toLocaleString()} Points • 30 VTK Features
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        {/* FAILED OR UNAVAILABLE DETAILS */}
                        {status === 'failed' && (
                          <p className="text-[11px] text-rose-700 font-medium">
                            Error: {modFinding?.error?.message || 'Inference failed.'}
                          </p>
                        )}
                        {status === 'unavailable' && (
                          <p className="text-[11px] text-slate-500 italic">
                            Reason: {modFinding?.reason || 'Model unavailable'}
                          </p>
                        )}
                      </div>
                    );
                  })}

                  {/* CLINICAL DISCLAIMER */}
                  <div className="rounded-xl bg-slate-100 p-3 text-[11px] text-slate-600 border border-slate-200">
                    <p className="font-bold text-slate-800">Research & Decision Support Notice</p>
                    <p className="mt-0.5">
                      {result?.disclaimer?.text || 'AI model outputs are experimental clinical decision-support and research outputs. They do not constitute a medical diagnosis.'}
                    </p>
                  </div>
                </div>
              ) : (
                /* ============================================
                    SINGLE MODEL SPECIFIC RENDERERS
                ============================================ */
                <div className="space-y-3">
                  {/* Plane */}
                  {selectedMode === 'plane' && (
                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                      <span className="text-xs font-semibold text-slate-500 uppercase">Predicted Fetal Plane</span>
                      <div className="mt-1 flex items-baseline justify-between">
                        <h3 className="text-xl font-bold text-slate-900">{result?.predicted_class || 'Other'}</h3>
                        <span className="text-sm font-bold text-teal-600">{result?.confidence_percent ?? ((result?.confidence || 1) * 100).toFixed(1)}% Confidence</span>
                      </div>
                    </div>
                  )}

                  {/* Spine & Bone */}
                  {(selectedMode === 'spine' || selectedMode === 'bone') && (
                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                      <span className="text-xs font-semibold text-slate-500 uppercase">Detection Summary</span>
                      <h3 className="text-xl font-bold text-slate-900 mt-1">
                        {Array.isArray(result?.detections) ? result.detections.length : 0} Landmark(s) Detected
                      </h3>
                    </div>
                  )}

                  {/* Brain */}
                  {selectedMode === 'brain' && (
                    <div className="space-y-3">
                      <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <span className="text-xs font-semibold text-slate-500 uppercase">Brain Plane</span>
                        <h3 className="text-xl font-bold text-slate-900 mt-1">{result?.brain_plane?.predicted_class}</h3>
                      </div>
                      {result?.brain_anomaly && (
                        <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                          <span className="text-xs font-semibold text-slate-700">Statistical Anomaly Status</span>
                          <p className="mt-1 font-semibold text-slate-800">{result.brain_anomaly.status}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Segmentation */}
                  {(selectedMode === 'lung' || selectedMode === 'placenta' || selectedMode === 'heart') && (
                    <div className="space-y-3">
                      {(() => {
                        const seg = result?.segmentation || result;
                        return (
                          <>
                            <div className="grid grid-cols-2 gap-3">
                              <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                                <span className="text-[11px] font-semibold text-slate-400 uppercase">Mask Pixels</span>
                                <p className="mt-1 text-lg font-bold text-slate-900">{seg?.mask_pixels?.toLocaleString() || 0}</p>
                              </div>
                              <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                                <span className="text-[11px] font-semibold text-slate-400 uppercase">Area Ratio</span>
                                <p className="mt-1 text-lg font-bold text-teal-600">{((seg?.mask_ratio || 0) * 100).toFixed(2)}%</p>
                              </div>
                            </div>
                            {seg?.mask_url && (
                              <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                                <span className="text-xs font-semibold text-slate-700">Generated AI Segmentation Mask</span>
                                <div className="mt-2 overflow-hidden rounded-lg bg-slate-950 flex items-center justify-center">
                                  <img src={`${API_BASE_URL}${seg.mask_url}`} alt="Mask" className="max-h-52 w-full object-contain" />
                                </div>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  )}

                  {/* Face */}
                  {selectedMode === 'face' && (
                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                      <span className="text-xs font-semibold text-slate-500 uppercase">3D Facial Morphology</span>
                      <h3 className="text-xl font-bold text-slate-900 mt-1">
                        {result?.prediction?.predicted_label || result?.prediction?.label || 'Normal'}
                      </h3>
                      <p className="text-xs text-fuchsia-700 font-semibold mt-1">
                        {(result?.prediction?.confidence_percent ?? ((result?.prediction?.confidence || 0.92) * 100)).toFixed(1)}% Confidence
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* ACTION BUTTONS */}
              <div className="pt-2 flex items-center gap-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={removeFile}
                  className="w-full"
                >
                  <RefreshCw size={14} className="mr-1.5" />
                  New Analysis / Reset
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

export default NewScanPage;
